import os
import shutil
import logging
import pytesseract
from SummarizerApp.models import User, Summary
from SummarizerApp.threading_variables import processing_thread_alive
from groq import Groq
from pathlib import Path

# Set the path to the tesseract executable
TESSERACT_PATH = 'C:\Program Files\Tesseract-OCR\\tesseract'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


logger = logging.getLogger('SummarizerApp')
key = os.getenv('GROQ_API_KEY', '').strip()
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
RECORDINGS_DIR = str(BASE_DIR) + "\\Recordings"

client = Groq(
    api_key = key
)


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



def process_recording(recording_path, wav_index, uid, title, time_start, time_end):
    processing_thread_alive.set()
    
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

    processing_thread_alive.clear()