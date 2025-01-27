from django.shortcuts import render
from rest_framework.decorators import api_view
import threading
from rest_framework.response import Response
from datetime import datetime
from .models import User, RecordingTime, Summary
from .serializers import UserSerializer, RecordingTimeSerializer, SummarySerializer
from .tasks.recording import record_meeting
from .tasks.scheduler import monitor_recording_schedule 
from .threading_variables import stop_recording, stop_monitoring, monitor_error_flag
from rest_framework import status
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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
from django.http import FileResponse
from reportlab.pdfgen import canvas
from io import BytesIO
from django.shortcuts import get_object_or_404


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

if not os.path.exists(RECORDINGS_DIR):
    os.mkdir(RECORDINGS_DIR)


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
        "title": "<string: meeting title>",  
        "window_name": "<string: browser window name>" or Null, #optional
    }
    '''
    global recording_thread, monitoring_thread

    title = request.data['title']
    window_name = request.data.get('window_name', None)
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
    recording_thread = threading.Thread(target=record_meeting, args=(MAX_RECORD_LENGTH, recording_path, uid, title, window_name), daemon=True)
    recording_thread.start()

    time.sleep(1)
    if recording_thread.is_alive():
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
        "title": "<string: meeting title>",
        "window_name": "<string: browser window name>" or Null, #optional
        "time_start": "<string: YYYY-MM-DDTHH:mm:ss>",
        "time_end": "<string: YYYY-MM-DDTHH:mm:ss>",
    }
    '''
    uid = request.session.get('uid', None)
    
    print(uid)

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

    serializer = RecordingTimeSerializer(data=data)
    if serializer.is_valid():
        recording_time = serializer.save()
        return Response({'message': 'Recording scheduled correctly', 'RID': recording_time.RID}, status=status.HTTP_201_CREATED) 
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  


@api_view(['GET'])
def get_recordings(request):
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)

    recordings = RecordingTime.objects.filter(UID=uid).order_by('-time_start')  
    page_size = 5  # number of recordings per page
    page_number = request.query_params.get('page', 1)  # get the page number from the request, default is 1

    paginator = Paginator(recordings, page_size)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)  # if page is not an integer deliver the first page
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)  # if page exceeds range deliver the last page

    serializer = RecordingTimeSerializer(page_obj.object_list, many=True)

    response_data = {
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': page_number,
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'results': serializer.data,
    }

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['POST'])
def delete_recording(request):
    '''
    request_body structure:
    {
        "RID": "<int: recording ID>",
    }
    '''
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        rid = request.data['RID']
        recording = RecordingTime.objects.get(RID=rid)
        if recording.UID_id != uid:
            return Response({'error': 'You do not have permission to delete this recording'}, status=status.HTTP_403_FORBIDDEN)
        else: 
            recording.delete()
            return Response({'message': 'Recording deleted'}, status=status.HTTP_200_OK) 

    except RecordingTime.DoesNotExist:
        return Response({'error': 'Recording does not exist'}, status=status.HTTP_404_NOT_FOUND) 

    except Exception as e:
        return Response({'error': f'Error deleting recording: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_summaries(request):
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)

    summaries = Summary.objects.filter(UID=uid).order_by('-time_start')
    page_size = 5
    page_number = request.query_params.get('page', 1)

    paginator = Paginator(summaries, page_size)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    serializer = SummarySerializer(page_obj.object_list, many=True)

    response_data = {
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': page_number,
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'results': serializer.data,
    }

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['POST'])
def delete_summary(request):
    '''
    request_body structure:
    {
        "SID": "<int: summary ID>",
    }
    '''
    uid = request.session.get('uid', None)

    if not uid:
        return Response({'message': 'No UID provided, log in the user'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        sid = request.data['SID']
        summary = Summary.objects.get(SID=sid)
        if summary.UID_id != uid:
            return Response({'error': 'You do not have permission to delete this summary'}, status=status.HTTP_403_FORBIDDEN)
        else: 
            summary.delete()
            return Response({'message': 'Summary deleted'}, status=status.HTTP_200_OK) 

    except Summary.DoesNotExist:
        return Response({'error': 'Summary does not exist'}, status=status.HTTP_404_NOT_FOUND) 

    except Exception as e:
        return Response({'error': f'Error deleting summary: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['POST'])
def generate_pdf(request):
    '''
    request_body structure:
    {
        "SID": "<int: summary ID>",
    }
    '''
    sid = request.data['SID']
    summary = get_object_or_404(Summary, SID=sid)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.setFont("Helvetica", 14)
    pdf.drawString(50, 800, f"Meeting Title: {summary.title}")
    pdf.drawString(50, 780, f"Start Time: {summary.time_start}")
    pdf.drawString(50, 760, f"End Time: {summary.time_end}")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 720, "Transcription:")
    pdf.setFont("Helvetica", 10)
    text_object = pdf.beginText(50, 700)
    text_object.setTextOrigin(50, 700)
    text_object.setFont("Helvetica", 10)

    # wrap transcription text to fit on the page
    transcription_lines = summary.transcription.split("\n")
    for line in transcription_lines:
        text_object.textLine(line)

    pdf.drawText(text_object)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 400, "Summary:")
    pdf.setFont("Helvetica", 10)
    text_object = pdf.beginText(50, 380)

    summary_lines = summary.summary.split("\n")
    for line in summary_lines:
        text_object.textLine(line)

    pdf.drawText(text_object)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    logger.info(f"Generated PDF for summary {summary.title}")

    return FileResponse(buffer, as_attachment=True, filename=f"{summary.title}_summary.pdf")