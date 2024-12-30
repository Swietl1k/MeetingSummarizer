import threading

stop_recording = threading.Event()
stop_monitoring = threading.Event()
monitor_error_flag = threading.Event()
processing_thread_alive = threading.Event()