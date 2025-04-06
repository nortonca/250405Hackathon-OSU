# eleven_tts.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVEN_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # default voice

def synthesize_speech(text, filename="static/output.mp3"):
    if not ELEVENLABS_API_KEY:
        print("⚠️ ELEVENLABS_API_KEY not found in .env – skipping TTS generation.")
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        print(f"❌ ElevenLabs API error: {response.status_code} - {response.text}")
        return None

    with open(filename, "wb") as f:
        f.write(response.content)

    return filename

