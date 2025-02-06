import os
import shutil
import logging
import pytesseract
from SummarizerApp.models import User, Summary
from SummarizerApp.threading_variables import processing_thread_alive
from groq import Groq
from pathlib import Path

# Set the path to the tesseract executable
TESSERACT_PATH = 'C:\\Program Files\\Tesseract-OCR\\tesseract'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


logger = logging.getLogger('SummarizerApp')
key = os.getenv('GROQ_API_KEY', '').strip()
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
RECORDINGS_DIR = str(BASE_DIR) + "\\Recordings"

client = Groq(
    api_key = key
)


def periodical_processing(recording_path, wav_index):
    transcription = transcribe(recording_path, wav_index)
    with open(f'{recording_path}\\transcription_{wav_index}.txt', 'w', encoding='utf-8') as file:
        file.write(transcription.text)
        logger.debug(f"transcription file saved wav_index={wav_index}")

    ocr_txt = ocr(recording_path)
    sum_txt = summarizeText(recording_path, wav_index, ocr_txt)
    with open(f'{recording_path}\\summary_{wav_index}.txt', 'w', encoding='utf-8') as f:
        f.write(sum_txt)
        logger.debug(f"summary file saved wav_index={wav_index}")


def transcribe(recording_path, wav_index):
    wav_path = f'{recording_path}\\audio_{wav_index}.wav'

    with open(wav_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(wav_path, file.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
        )
        
    return transcription
    

def ocr(recording_path):
    '''
    Find all screenshots in the recording path, ocr and combine them into one text file
    After combining the text files, remove the screenshots
    '''
    text_combined = ""
    paths = find_files_with_keyword(recording_path, 'screenshot') 

    for path in paths:
        text = pytesseract.image_to_string(path)
        text_combined += text
        os.remove(path)

    return text_combined
    

def summarizeText(recording_path, wav_index, txt):
    completion = client.chat.completions.create(
        model="llama3-8b-8192",  
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a summarization assistant for text derived from OCR of online meeting screenshots. "
                    "Your task is to return a concise and relevant summary of the content presented in a meeting. "
                    "Do not include filler or explanatory text (e.g., 'This appears to be...', or 'Based on the text provided...'). "
                    "Ensure your response only includes the summary text without any introductory or concluding remarks."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Please summarize the following text strictly and concisely:\n{txt}\n\n"
                    "Only return the summary text, nothing else."
                )
            }
        ],
        temperature=0.7,  # keep responses focused and consistent
        max_tokens=512,
        top_p=1,
        stream=True,
        stop=None,
    )

    summary = ""
    for chunk in completion:
        summary += chunk.choices[0].delta.content or ""

    return summary

    

def process_recording(recording_path, wav_index, uid, title, time_start, time_end):
    processing_thread_alive.set()
    
    # add all transcribed text from audio recording to one file
    combined_transcription = ""
    for i in range(wav_index):
        with open(f'{recording_path}\\transcription_{i}.txt', 'r', encoding="utf-8") as file:
            combined_transcription += file.read()

    combined_summary = ""
    for i in range(wav_index):
        with open(f'{recording_path}\\summary_{i}.txt', 'r', encoding="utf-8") as file:
            combined_summary += file.read()



    completion = client.chat.completions.create(
        model="llama3-8b-8192",  
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant responsible for cleaning up and refining text. "
                    "Your task is to remove any repetitive phrases or unnecessary text from summaries while keeping only the essential content. "
                    "For example, remove phrases like 'Here is the summary:' or any similar opening or closing remarks. "
                    "Ensure the result is a clean, concise, and polished version of the provided text."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Please clean up the following summary text by removing repetitive phrases or irrelevant lines:\n{combined_summary}\n\n"
                    "Return only the cleaned-up summary text without any opening or closing remarks."
                    "If your summary is too short to be good, expand on the topics provided in the text to reach around a 100 words."
                )
            }
        ],
        temperature=0.7,
        max_tokens=512,
        top_p=1,
        stream=True,
        stop=None,
    )

    cleaned_summary = ""
    for chunk in completion:
        cleaned_summary += chunk.choices[0].delta.content or ""

    #delete files used for process
    shutil.rmtree(recording_path)

    try:
        user_instance = User.objects.get(id=uid)

        summary = Summary(
            UID=user_instance,
            title=title,
            time_start=time_start,
            time_end=time_end,
            transcription=combined_transcription,
            summary=cleaned_summary,
        )
        summary.save()

    except Exception as e:
            logging.error(f"Error saving summary: {e} \n files saved localy in: \n {recording_path}")
            os.mkdir(recording_path)
            
            # Save the transcription and summary locally if saving the summary fails
            with open(f'{recording_path}\\transcription_combined.txt', 'w') as file:
                file.write(combined_transcription)
            
            with open(f'{recording_path}\\summarized_text.txt', 'w') as f:
                f.write(combined_summary)

    processing_thread_alive.clear()


def find_files_with_keyword(directory, keyword):
    """
    Returns a list of file paths in the provided directory that contain the keyword in their filename.
    """
    matching_files = []

    for filename in os.listdir(directory):
        if keyword in filename:
            matching_files.append(os.path.join(directory, filename))
    return matching_files