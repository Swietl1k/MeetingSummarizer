from django.shortcuts import render
from rest_framework.decorators import api_view
import threading
from rest_framework.response import Response
from datetime import datetime
from .models import User, RecordingTime, Summary
from .serializers import UserSerializer, RecordingTimeSerializer
from .tasks.audio import record_audio
from .tasks.scheduler import monitor_recording_schedule 
from .threading_variables import stop_recording, stop_monitoring, monitor_error_flag
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

monitoring_thread = None
recording_thread = None
logger = logging.getLogger('SummarizerApp')



@api_view(['GET'])
def start_monitoring(request):
    global monitoring_thread
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)

    ####### START MONITORING THREAD
    monitoring_thread = threading.Thread(target=monitor_recording_schedule, args=(uid,), daemon=True)
    monitoring_thread.start()
    #######

    if monitoring_thread.is_alive() and not monitor_error_flag.is_set():
        return Response({'message': 'monitoring started'}, status=status.HTTP_200_OK)

    return Response({'error': 'monitoring thread failed to start'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def test(request):
    return Response({'uid': f'{request.session.get("uid", None)}'})


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
    global recording_thread, monitoring_thread

    title = request.data['title']
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)

    if recording_thread and recording_thread.is_alive():
        return Response({'message': 'Recording already running.'}, status=status.HTTP_409_CONFLICT) 

    random_id = random.randint(10000, 99999) #making a random ID to ensure no collisions with dir names 
    stop_monitoring.set()
    if monitoring_thread and monitoring_thread.is_alive():
        monitoring_thread.join() # wait for the monitor thread to finish

    recording_path = f'{RECORDINGS_DIR}\\{random_id}'
    os.mkdir(recording_path)

    stop_recording.clear()
    recording_thread = threading.Thread(target=record_audio, args=(MAX_RECORD_LENGTH, recording_path, uid, title), daemon=True)
    recording_thread.start()

    return Response({"message": "Recording started."}, status=status.HTTP_202_ACCEPTED)  


@api_view(['GET'])
def end_recording(request):
    global recording_thread
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        current_time = datetime.now()
        recording = RecordingTime.objects.get(UID=uid, time_start__lte=current_time, time_end__gte=current_time)
        recording.delete()
        stop_recording.set()
        if recording_thread and recording_thread.is_alive():
            recording_thread.join()

        return Response({"message": "Recording stopped."}, status=status.HTTP_200_OK)  

    except RecordingTime.DoesNotExist:
        if recording_thread and recording_thread.is_alive(): # check for manually started recordings 
            stop_recording.set()
            return Response({"message": "Recording stopped."}, status=status.HTTP_200_OK)  
        
        return Response({"message": "No Recording is taking place currently"}, status=status.HTTP_404_NOT_FOUND)  
    
    except Exception as e:
        return Response({"error": f"Error while stopping the recording: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def schedule_recording(request):
    '''
    request_body structure:
    {   
        #"UID": "<int: User ID>",
        "title": "<string: example>",
        "time_start": "<string: YYYY-MM-DDTHH:mm:ss>",
        "time_end": "<string: YYYY-MM-DDTHH:mm:ss>",
    }
    '''
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)


    try:
        title = request.data['title']
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
