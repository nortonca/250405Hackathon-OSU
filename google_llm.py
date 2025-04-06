# File: google_llm.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

def call_google_llm(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "key": GOOGLE_API_KEY
    }
    data = {
        "contents": [ {
            "role": "user",
            "parts": [ { "text": prompt } ]
        } ]
    }

    response = requests.post(url, headers=headers, params=params, json=data)

    if response.status_code != 200:
        raise Exception(f"Google API error: {response.status_code} - {response.text}")

    json_response = response.json()
    return json_response["candidates"][0]["content"]["parts"][0]["text"]
