from django.shortcuts import render
from rest_framework.decorators import api_view
import threading
from rest_framework.response import Response
from datetime import datetime
from .models import User, RecordingTime
from .serializers import UserSerializer, RecordingTimeSerializer
from rest_framework import status
import time
import pyaudiowpatch as pyaudio
import wave
from pathlib import Path
from groq import Groq
from PIL import ImageGrab
import os



CHUNK_SIZE = 1024
MAX_RECORD_LENGTH = 3 * 60 * 60  # 3 hours
MONITOR_INTERVAL = 10
BASE_DIR = Path(__file__).resolve().parent.parent.parent
RECORDINGS_DIR = str(BASE_DIR) + "\\Recordings"
SCREENSHOT_INTERVAL = 20 # secconds

stop_recording = threading.Event()
stop_monitoring = threading.Event()
recording_thread = None

key_file = open(f'{BASE_DIR}\\key.txt', 'r')
key = key_file.read()

client = Groq(
    api_key = key
)



def monitor_recording_schedule():
    global stop_monitoring, stop_recording
    stop_monitoring.clear()

    while not stop_monitoring.is_set():
        current_time = datetime.now()
        print(current_time)

        for rt in RecordingTime.objects.all():
            if rt.time_start <= current_time <= rt.time_end:
                recording_length = int((rt.time_end - rt.time_start).total_seconds())
                recording_path = f'{RECORDINGS_DIR}\\{(str(rt.time_start)).replace(" ", "-").replace(":", "-")}'
                os.mkdir(recording_path)
                stop_recording.clear()
                recording_thread = threading.Thread(target=record_audio, args=(recording_length, recording_path), daemon=True)
                recording_thread.start()
                stop_monitoring.set()

        time.sleep(MONITOR_INTERVAL)


####### START MONITORING THREAD
monitoring_thread = threading.Thread(target=monitor_recording_schedule, daemon=True)
monitoring_thread.start()
#######


def record_audio(recording_length, recording_path):
    global stop_recording
    wav_path = recording_path + '\\recording.wav'
    txt_path = recording_path + '\\recording.txt'
    with pyaudio.PyAudio() as p:

        try:
            # Get default WASAPI info
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            print("Looks like WASAPI is not available on the system. Exiting...")
            exit()

        # Get default WASAPI speakers
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        if not default_speakers["isLoopbackDevice"]:
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
            else:
                print("Default loopback output device not found.\n\nRun `python -m pyaudiowpatch` to check available devices.\nExiting...\n")
                exit()

        print(f"Recording from: ({default_speakers['index']}){default_speakers['name']}")

        wave_file = wave.open(wav_path, 'wb')
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
            print(f"The next {recording_length} seconds will be written to {wav_path}")

            for i in range(recording_length):
                if i % SCREENSHOT_INTERVAL == 0:
                    screenshot = ImageGrab.grab()
                    screenshot.save(f'{recording_path}\\screenshot{i // SCREENSHOT_INTERVAL}.png')

                if stop_recording.is_set():
                    break
                time.sleep(1)

        screenshot.close()
        wave_file.close()
        transcription = transcribe(wav_path)
        with open(txt_path, 'w') as f:
            f.write(transcription)

        monitoring_thread = threading.Thread(target=monitor_recording_schedule, daemon=True)
        monitoring_thread.start()


def transcribe(file_path):
    with open(file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(file_path, file.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
        )
        
    return transcription.text
    

@api_view(['GET'])
def start_recording(request):
    global stop_recording, stop_monitoring, recording_thread

    if recording_thread and recording_thread.is_alive():
        return Response({'message': 'Recording already running.'}, status=status.HTTP_409_CONFLICT) 

    stop_monitoring.set()
    monitoring_thread.join() # wait for the monitor thread to finish
    current_time = datetime.now()
    recording_path = f'{RECORDINGS_DIR}\\{(str(current_time)).replace(" ", "-").replace(":", "-")}.wav'
    os.mkdir(recording_path)

    stop_recording.clear()
    recording_thread = threading.Thread(target=record_audio, args=(MAX_RECORD_LENGTH, recording_path), daemon=True)
    recording_thread.start()

    return Response({"message": "Recording started."}, status=status.HTTP_202_ACCEPTED)  


@api_view(['GET'])
def end_recording(request):
    global stop_recording, recording_thread

    try:
        current_time = datetime.now()
        recording = RecordingTime.objects.get(time_start__lte=current_time, time_end__gte=current_time)
        recording.delete()
        stop_recording.set()
        return Response({"message": "Recording stopped."}, status=status.HTTP_200_OK)  

    except RecordingTime.DoesNotExist:
        if recording_thread and recording_thread.is_alive(): # check for manually started recordings 
            stop_recording.set()
            return Response({"message": "Recording stopped."}, status=status.HTTP_200_OK)  
        
        return Response({"message": "No Recording is taking place currently"}, status=status.HTTP_404_NOT_FOUND)  


@api_view(['POST'])
def schedule_recording(request):
    '''
    request_body structure:
    {
        "time_start: "<string: YYYY-MM-DDTHH:mm:ss>",
        "time_end: "<string: YYYY-MM-DDTHH:mm:ss>",
    }
    '''

    try:
        time_start = request.data['time_start'].replace(':', '-').replace('T', '-')
        time_end = request.data['time_end'].replace(':', '-').replace('T', '-')
        time_start = datetime.strptime(time_start, "%Y-%m-%d-%H-%M-%S")
        time_end = datetime.strptime(time_end, "%Y-%m-%d-%H-%M-%S")

    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DDTHH:mm:ss'}, status=status.HTTP_400_BAD_REQUEST)  

    time_difference = time_end - time_start
    if time_start > time_end:
        return Response({'error': 'time_end is before time_start'}, status=status.HTTP_400_BAD_REQUEST) 
    elif time_start == time_end:
        return Response({'error': 'time_end is equal to time_start'}, status=status.HTTP_400_BAD_REQUEST)  
    elif time_difference.total_seconds() <  MONITOR_INTERVAL*2:
        return Response({'error': f'Total meeting time must be at least {MONITOR_INTERVAL*2} secconds long'}, status=400)

    for rt in RecordingTime.objects.all():
        starts_within_existing = rt.time_start <= time_start <= rt.time_end
        ends_within_existing = rt.time_start <= time_end <= rt.time_end
        overlaps_existing = time_start < rt.time_start and time_end > rt.time_end

        if starts_within_existing or ends_within_existing or overlaps_existing:
            return Response({'message': 'Invalid time: overlaps with existing schedule'}, status=status.HTTP_409_CONFLICT)  


    serializer = RecordingTimeSerializer(data=request.data)
    if serializer.is_valid():
        recording_time = serializer.save()
        return Response({'message': 'Recording scheduled correctly', 'RID': recording_time.RID}, status=status.HTTP_201_CREATED) 
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  
