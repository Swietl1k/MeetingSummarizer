import threading
import time
import os
import pyaudiowpatch as pyaudio
import wave
from datetime import datetime
import logging
from pathlib import Path
from .processing import periodical_processing, process_recording 
from SummarizerApp.threading_variables import stop_recording, periodical_thread_alive
from .screenshot import take_screenshot


logger = logging.getLogger('SummarizerApp')
CHUNK_SIZE = 1024
MAX_RECORD_LENGTH = 3 * 60 * 60  # 3 hours
MONITOR_INTERVAL = 20
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
RECORDINGS_DIR = str(BASE_DIR) + "\\Recordings"
AI_API_INTERVAL = 90 # max 90 secconds so it doesnt exceed api token limits
SCREENSHOT_INTERVAL = 20 # secconds between each screenshot while recording a meeting




def record_meeting(recording_length, recording_path, uid, title, window_name = None):
    from .scheduler import monitor_recording_schedule
    current_length = 0
    wav_index = 0
    time_start = datetime.now()
    stop_recording.clear()

    with pyaudio.PyAudio() as p:

        try:
            # Get default WASAPI info
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            logger.critical("Looks like WASAPI is not available on the system. Exiting...")
            exit()

        # Get default WASAPI speakers
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        if not default_speakers["isLoopbackDevice"]:
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
            else:
                logger.critical("Default loopback output device not found.\n\nRun `python -m pyaudiowpatch` to check available devices.\nExiting...\n")
                exit()

        logger.info(f"Recording from: ({default_speakers['index']}){default_speakers['name']}")

        while current_length < recording_length and not stop_recording.is_set():
            wave_file = wave.open(f'{recording_path}\\audio_{wav_index}.wav', 'wb')
            wave_file.setnchannels(default_speakers["maxInputChannels"])
            wave_file.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
            wave_file.setframerate(int(default_speakers["defaultSampleRate"]))

            def callback(in_data, frame_count, time_info, status):
                wave_file.writeframes(in_data)
                return (in_data, pyaudio.paContinue)

            with p.open(format=pyaudio.paInt16,
                        channels=default_speakers["maxInputChannels"],
                        rate=int(default_speakers["defaultSampleRate"]),
                        frames_per_buffer=CHUNK_SIZE,
                        input=True,
                        input_device_index=default_speakers["index"],
                        stream_callback=callback
                        ) as stream:
                #print(f"The next {recording_length} seconds will be written to {wav_path}")

                if recording_length - current_length >= AI_API_INTERVAL:
                    time_wait = AI_API_INTERVAL
                else:
                    time_wait = recording_length - current_length

                
                os.mkdir(f'{recording_path}\\screenshots_{wav_index}')
                for i in range(time_wait):
                    if i % SCREENSHOT_INTERVAL == 0:
                            screenshot_path = f'{recording_path}\\screenshots_{wav_index}\\{i // SCREENSHOT_INTERVAL}.png'
                            take_screenshot(screenshot_path, window_name)
                    elif stop_recording.is_set():
                            break
                    
                    time.sleep(1)

            wave_file.close()

            period_process_thread = threading.Thread(target=periodical_processing, args=(recording_path, wav_index), daemon=True)
            period_process_thread.start()
            logger.debug(f'periodical processing thread started, wav_index={wav_index}')

            current_length += AI_API_INTERVAL
            wav_index += 1

        time_end = datetime.now()
        #period_process_thread.join()
        process_thread = threading.Thread(target=process_recording, args=(recording_path, wav_index, uid, title, time_start, time_end), daemon=True)
        process_thread.start()

        monitoring_thread = threading.Thread(target=monitor_recording_schedule, args=(uid,), daemon=True)
        monitoring_thread.start()