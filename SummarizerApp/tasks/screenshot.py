import time
import pygetwindow as gw
import pyautogui
from PIL import ImageGrab
import logging 

logger = logging.getLogger('SummarizerApp')

def take_screenshot(screenshot_path, window_name = None):  
    screenshot = ImageGrab.grab()
    screenshot.save(screenshot_path)
    logger.info(f"Taking screenshot")


    '''
    # take a screenshot of a window with a given name, or the whole screen if window_name is None
    if window_name is None:
        print("reg")
        screenshot = ImageGrab.grab()
        screenshot.save(screenshot_path)
    else:
        try:
            window = gw.getWindowsWithTitle(window_name)[0]
            print(f'window: {window}')
            if window.isMinimized:
                window.restore()

            window.activate()
            time.sleep(0.5)
            screenshot = pyautogui.screenshot(region=window.box)
            screenshot.save(screenshot_path)
        except Exception as e:
            logger.error(f"Error taking screenshot of window: {str(e)}")
            screenshot = ImageGrab.grab()
            screenshot.save(screenshot_path)
            '''
