from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import time
import os
import logging

# Configure Logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Configuration
ASSEMBLYAI_API_KEY = "7d34c29015e047398f2e089ca90c6e3e"
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "Eomer/gpt-3.5-turbo"

app = FastAPI()

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper Functions
def upload_audio_to_assembly(file_path):
    upload_url = "https://api.assemblyai.com/v2/upload"
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    with open(file_path, 'rb') as f:
        response = requests.post(upload_url, headers=headers, files={'file': f})
    response.raise_for_status()
    return response.json()["upload_url"]

def request_transcription(audio_url):
    endpoint = "https://api.assemblyai.com/v2/transcript"
    headers = {"authorization": ASSEMBLYAI_API_KEY, "content-type": "application/json"}
    json_data = {"audio_url": audio_url, "language_code": "en_us"}
    response = requests.post(endpoint, json=json_data, headers=headers)
    response.raise_for_status()
    return response.json()["id"]

def poll_transcription(transcript_id, max_retries=10):
    endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    retries = 0
    while retries < max_retries:
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        status = response.json()["status"]
        if status == "completed":
            return response.json()["text"]
        elif status == "error":
            raise Exception("Transcription failed.")
        else:
            time.sleep(10)
            retries += 1
    raise Exception("Transcription timed out after multiple retries.")

def analyze_with_ollama(transcription_text):
    prompt = f"""
    Analyze the following text:
    "{transcription_text}"
    Classify it as Fraud, Spam, Bot, or None.
    """
    headers = {"Content-Type": "application/json"}
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "max_tokens": 500}
    try:
        response = requests.post(OLLAMA_API_URL, headers=headers, json=payload, stream=True)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with Ollama API: {str(e)}")

    final_response = ""
    for line in response.iter_lines(decode_unicode=True):
        if line:
            try:
                data = json.loads(line)
                final_response += data.get("response", "")
            except json.JSONDecodeError:
                continue

    if not final_response.strip():
        raise HTTPException(status_code=500, detail="Ollama API returned an empty response.")
    return final_response.strip()

# API Routes
@app.post("/analyze/")
async def analyze_call(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"
    try:
        if not file.filename.endswith(('.mp3', '.wav')):
            raise HTTPException(status_code=400, detail="Invalid file format. Please upload an MP3 or WAV file.")

        with open(temp_file_path, "wb") as f:
            f.write(file.file.read())

        audio_url = upload_audio_to_assembly(temp_file_path)
        transcript_id = request_transcription(audio_url)
        transcription_text = poll_transcription(transcript_id)
        ollama_response = analyze_with_ollama(transcription_text)

        return JSONResponse(content={"transcription": transcription_text, "analysis": ollama_response})

    except Exception as e:
        logger.error("Error during analysis: %s", str(e))
        return JSONResponse(
            content={"error": str(e), "message": "An error occurred during analysis. Check the backend logs for more details."},
            status_code=500
        )

    finally:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as cleanup_error:
                logger.error("Error cleaning up temporary file: %s", str(cleanup_error))
