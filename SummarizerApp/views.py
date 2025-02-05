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
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.lib import utils
from io import BytesIO
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth import authenticate, login as django_login

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

    data = request.data
    try:
        user = User.objects.create(
            username=data['username'],
            email=data['email'],
            password=make_password(data['password'])  # Hash the password
        )
        return Response({'message': 'User registered successfully', 'UID': user.id}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



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
    print("login")

    try:
        user = authenticate(username=username, password=password)
        if user is not None:
            django_login(request, user)  # Log the user in and create a session
            print(user.id)
            request.session["uid"] = user.id
            return Response({'message': 'Login successful', 'UID': user.id, 'username': user.username}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid login or password'}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
def logout(request):
    if not request.session.get('uid', None):
        return Response({'message': 'No user logged in'}, status=status.HTTP_401_UNAUTHORIZED)
    
    request.session.pop('uid', None)
    return Response({'message': 'User logged out'}, status=status.HTTP_200_OK)



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
    serializer = RecordingTimeSerializer(recordings, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


    ''' 
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
    '''


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
    serializer = RecordingTimeSerializer(summaries, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)

    '''
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
    '''

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
    pdf = canvas.Canvas(buffer, pagesize=letter)

    page_width, page_height = letter
    margin = 50
    text_width = page_width - 2 * margin
    text_height = page_height - 100  # Leaving space for header/footer

    y_position = page_height - 50  # Start position for text

    def add_wrapped_text(pdf, text, x, y, width, font_size, line_spacing=12):
        pdf.setFont("Helvetica", font_size)
        lines = simpleSplit(text, "Helvetica", font_size, width)
        for line in lines:
            if y < margin:  # If text goes below margin, create a new page
                pdf.showPage()
                pdf.setFont("Helvetica", font_size)
                y = page_height - margin
            pdf.drawString(x, y, line)
            y -= line_spacing
        return y

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin, y_position, f"Meeting Title: {summary.title}")
    y_position -= 20
    pdf.drawString(margin, y_position, f"Start Time: {summary.time_start.strftime('%Y-%m-%d %H:%M:%S')}")
    y_position -= 20
    pdf.drawString(margin, y_position, f"End Time: {summary.time_end.strftime('%Y-%m-%d %H:%M:%S')}")
    y_position -= 30

    # Add transcription
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y_position, "Audio transcription:")
    y_position -= 20
    y_position = add_wrapped_text(
        pdf, summary.transcription, margin, y_position, text_width, 10, line_spacing=12
    )

    # Add summary
    y_position -= 30
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin, y_position, "Summary of screen recording:")
    y_position -= 20
    y_position = add_wrapped_text(
        pdf, summary.summary, margin, y_position, text_width, 10, line_spacing=12
    )

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    logger.info(f"Generated PDF for summary {summary.title}")

    return FileResponse(buffer, as_attachment=True, filename=f"{summary.title}_summary.pdf")