from django.shortcuts import render
from rest_framework.decorators import api_view
import threading
from rest_framework.response import Response
from datetime import datetime
from .models import User, RecordingTime, Summary
from .serializers import UserSerializer, RecordingTimeSerializer
from rest_framework import status
import time
import pyaudiowpatch as pyaudio
import wave
from pathlib import Path
from groq import Groq
from PIL import ImageGrab
import os
import pytesseract
import random 
import shutil
import logging 


CHUNK_SIZE = 1024
MAX_RECORD_LENGTH = 3 * 60 * 60  # 3 hours
MONITOR_INTERVAL = 20
BASE_DIR = Path(__file__).resolve().parent.parent.parent
RECORDINGS_DIR = str(BASE_DIR) + "\\Recordings"
RECORDING_INTERVAL = 60 # max 60 secconds so it doesnt exceed groq whisper limits on audio recording length
SCREENSHOT_INTERVAL = 20 # secconds between each screenshot while recording a meeting

stop_recording = threading.Event()
stop_monitoring = threading.Event()
recording_thread = None
logger = logging.getLogger('SummarizerApp')

pytesseract.pytesseract.tesseract_cmd = 'C:\Program Files\Tesseract-OCR\\tesseract'
key_file = open(f'{BASE_DIR}\\key.txt', 'r')
key = key_file.read()

client = Groq(
    api_key = key
)



def monitor_recording_schedule(uid):
    global stop_monitoring, stop_recording
    stop_monitoring.clear()

    while not stop_monitoring.is_set():
        current_time = datetime.now()
        print(current_time)

        try:
            recording_times = RecordingTime.objects.get(UID=uid)

            for rt in recording_times:
                if rt.time_start <= current_time <= rt.time_end:
                    recording_length = int((rt.time_end - current_time).total_seconds())
                    recording_path = f'{RECORDINGS_DIR}\\{rt.RID}'

                    try:
                        os.mkdir(recording_path)
                    except FileExistsError:
                        logger.warning(f'directory already exists: {recording_path}')

                    stop_recording.clear()
                    recording_thread = threading.Thread(target=record_audio, args=(recording_length, recording_path, uid, rt.title), daemon=True)
                    recording_thread.start()
                    stop_monitoring.set()

                elif rt.time_end < current_time:
                    rid = rt.RID
                    rt.delete()
                    logger.info(f'RecordingTime deleted RID={rid}')

        except RecordingTime.DoesNotExist: 
            logger.info('no recordings available')
        except Exception as e:
            logger.error(f'error in the monitoring thread: {str(e)}')

        time.sleep(MONITOR_INTERVAL)





def record_audio(recording_length, recording_path, uid, title):
    global stop_recording
    current_length = 0
    wav_index = 0
    time_start = datetime.now()
    screenshot = ImageGrab.grab()


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

                if recording_length - current_length >= RECORDING_INTERVAL:
                    time_wait = RECORDING_INTERVAL
                else:
                    time_wait = recording_length - current_length

                for i in range(time_wait):
                    if i % SCREENSHOT_INTERVAL == 0:
                            screenshot.save(f'{recording_path}\\screenshot{i // SCREENSHOT_INTERVAL}.png')
                            logger.info('screenshot')
                    elif stop_recording.is_set():
                            break
                    
                    time.sleep(1)

            time_end = datetime.now()
            wave_file.close()

            transcription_thread = threading.Thread(target=transcribe, args=(recording_path, wav_index), daemon=True)
            for i in range(10):
                # when recording is a couple seconds longer than whole minutes, this waits up to 10s for the last transcription to finish
                # if not than runs transcription thread immediately
                if not transcription_thread.is_alive():
                    logger.debug(f'transcription wav_index={wav_index}')
                    transcription_thread.start()
                    break

                if i == 9:
                    logger.error("transcription thread didnt terminate in time")

                time.sleep(1)

            current_length += RECORDING_INTERVAL
            wav_index += 1

 
        screenshot.close()
        transcription_thread.join()
        monitoring_thread = threading.Thread(target=monitor_recording_schedule, args=(uid,), daemon=True)
        monitoring_thread.start()

        process_thread = threading.Thread(target=process_recording, args=(recording_path, wav_index, uid, title, time_start, time_end), daemon=True)
        process_thread.start()


def transcribe(recording_path, wav_index):
    wav_path = f'{recording_path}\\audio_{wav_index}.wav'
    txt_path = f'{recording_path}\\transcription_{wav_index}.txt'

    with open(wav_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(wav_path, file.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
        )
        
    with open(txt_path, 'w') as file:
        file.write(transcription.text)
        logger.debug(f"transcription file saved wav_index={wav_index}")



def process_recording(recording_path, wav_index, uid, title, time_start, time_end):
    ocr(recording_path)
    txt_summarized = summarizeText(recording_path)

    # add all transcribed text from audio recording to one file
    combined_transcription = ""
    for i in range(wav_index):
        with open(f'{recording_path}\\transcription_{i}.txt', 'r') as file:
            combined_transcription += file.read()

    #delete files used for process
    shutil.rmtree(recording_path)

    try:
        user_instance = User.objects.get(UID=uid)

        summary = Summary(
            UID=user_instance,
            title=title,
            time_start=time_start,
            time_end=time_end,
            transcription=combined_transcription,
            summary=txt_summarized,
        )
        summary.save()

    except Exception as e:
            logging.error(f"Error saving summary: {e} \n files saved localy in: \n {recording_path}")
            os.mkdir(recording_path)
            
            # Save the transcription and summary locally if saving the summary fails
            with open(f'{recording_path}\\transcription_combined.txt', 'w') as file:
                file.write(combined_transcription)
            
            with open(f'{recording_path}\\summarized_text.txt', 'w') as f:
                f.write(txt_summarized)


def ocr(recording_path):
    text_combined = ""
    i = 0
    while os.path.exists(f'{recording_path}\\screenshot{i}.png'):
        text = pytesseract.image_to_string(f'{recording_path}\\screenshot{i}.png')
        text_combined += text
        with open(f'{recording_path}\\screenshot{i}.txt', 'w', encoding='utf-8') as f:
            f.write(text)

        i+=1

    with open(f'{recording_path}\\text_combined.txt', 'w', encoding='utf-8') as f:
            f.write(text_combined)


def summarizeText(recording_path):
    try:
        with open(f'{recording_path}\\text_combined.txt', 'r', encoding='utf-8') as file:
            text = file.read()

        completion = client.chat.completions.create(
            model="llama3-8b-8192",  
            messages=[
                {"role": "system", "content": "You need to summarize text that comes from ocr of online meeting screenshots (keep in mind that the screenshots are taken periodically and dont only capture the presentation but also the meeting app interface, sumarize content only relevant to the presentation)."},
                {"role": "user", "content": f"Please summarize the following text:\n{text}"}
            ],
            temperature=1,  # Adjust for creativity (lower values are more deterministic)
            max_tokens=512,  # Limit the output length of the summary
            top_p=1,
            stream=True,
            stop=None,
        )

        summary = ""
        for chunk in completion:
            summary += chunk.choices[0].delta.content or ""

        return summary

    except FileNotFoundError:
        logger.error("text_combined.txt not found ")
        return "Error: The specified file was not found."
    except Exception as e:
        logger.error(str(e))
        return f"An error occurred: {str(e)}"


@api_view(['POST'])
def start_monitoring(request):
    '''
    {
    #"UID": <int:>,
    }
    '''
    global monitoring_thread
    
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)

    ####### START MONITORING THREAD
    monitoring_thread = threading.Thread(target=monitor_recording_schedule, args=(uid,), daemon=True)
    monitoring_thread.start()
    #######
    return Response({'message': 'monitor started'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def test(request):
    print('tesseract: ')
    print(pytesseract.image_to_string(f'{RECORDINGS_DIR}\\test\\screenshot0.0.png'))
    return Response({'message': 'testting'})


@api_view(['POST'])
def register(request):
    '''
    {
    "email": <string: example>,
    "username": <string: example>,
    "password": <string: example>,
    }
    '''

    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({'message': 'User registered successfully', 'UID': user.UID}, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
def login(request):
    '''
    {
    "username": <string: example>
    "password": <string: example>,
    }
    '''

    username = request.data['username']
    password = request.data['password']

    try:
        user = User.objects.get(username=username)
        if user.check_password(password):
            request.session['uid'] = user.UID
            return Response({'message': 'Login successful', 'UID': user.UID, 'username': user.username}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid login or password'}, status=status.HTTP_401_UNAUTHORIZED)
    except User.DoesNotExist:
        return Response({'error': 'User does not exist'}, status=status.HTTP_401_UNAUTHORIZED)
    

@api_view(['GET'])
def logout(request):
    request.session.pop('uid', None)
    return Response({'error': 'User logged out'}, status=status.HTTP_200_OK)



@api_view(['POST'])
def start_recording(request):
    '''
    request_body structure:
    {
        "title": "<string: example>",  
        #"UID": "<int:>",  
    }
    '''

    global stop_recording, stop_monitoring, recording_thread, monitoring_thread
    title = request.data['title']
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)

    if recording_thread and recording_thread.is_alive():
        return Response({'message': 'Recording already running.'}, status=status.HTTP_409_CONFLICT) 

    random_id = random.randint(10000, 99999) #making a random ID to ensure no collisions with dir names 
    stop_monitoring.set()
    monitoring_thread.join() # wait for the monitor thread to finish
    recording_path = f'{RECORDINGS_DIR}\\{random_id}'
    os.mkdir(recording_path)

    stop_recording.clear()
    recording_thread = threading.Thread(target=record_audio, args=(MAX_RECORD_LENGTH, recording_path, uid, title), daemon=True)
    recording_thread.start()

    return Response({"message": "Recording started."}, status=status.HTTP_202_ACCEPTED)  


@api_view(['GET'])
def end_recording(request):
    global stop_recording, recording_thread
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        current_time = datetime.now()
        recording = RecordingTime.objects.get(UID=uid, time_start__lte=current_time, time_end__gte=current_time)
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
        #"UID": "<int: User ID>",
        #"title": "<string: example>",
        "time_start": "<string: YYYY-MM-DDTHH:mm:ss>",
        "time_end": "<string: YYYY-MM-DDTHH:mm:ss>",
    }
    '''
    uid = request.session.get('uid', None)
    title = 'todo!()'

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)


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


    data = request.data.copy()
    data['UID'] = uid
    data['title'] = title

    serializer = RecordingTimeSerializer(data=data)
    if serializer.is_valid():
        recording_time = serializer.save()
        return Response({'message': 'Recording scheduled correctly', 'RID': recording_time.RID}, status=status.HTTP_201_CREATED) 
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  
