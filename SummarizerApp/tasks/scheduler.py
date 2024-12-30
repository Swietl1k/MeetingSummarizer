from pathlib import Path
import os
import logging
import threading
from SummarizerApp.models import RecordingTime
import time
from SummarizerApp.threading_variables import stop_recording, stop_monitoring, monitor_error_flag, processing_thread_alive
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
RECORDINGS_DIR = str(BASE_DIR) + "\\Recordings"
MONITOR_INTERVAL = 20
logger = logging.getLogger('SummarizerApp')



def monitor_recording_schedule(uid):
    from .audio import record_audio
    stop_monitoring.clear()
    monitor_error_flag.clear()

    while not stop_monitoring.is_set():
        try:
            current_time = datetime.now()
            print(current_time)
            recording_times = RecordingTime.objects.filter(UID=uid)
            #print(recording_times)

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

                    if os.path.exists(f'{RECORDINGS_DIR}\\{rid}') and not processing_thread_alive.is_set():
                        os.mkdir(f'{RECORDINGS_DIR}\\{rid}')
                    
                    logger.info(f'RecordingTime deleted RID={rid}')

        except RecordingTime.DoesNotExist: 
            logger.info('no recordings available')
        except Exception as e:
            monitor_error_flag.set()
            logger.error(f'error in the monitoring thread: {str(e)}')

        time.sleep(MONITOR_INTERVAL)