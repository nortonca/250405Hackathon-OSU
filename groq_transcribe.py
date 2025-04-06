import os
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

client = Groq(api_key=GROQ_API_KEY)

def transcribe_audio(file_path):
    """Transcribe audio to text using Groq's API"""
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=audio_file,
            model="distil-whisper-large-v3-en"
        )
        return response.text

def get_vision_response(transcription, image_data):
    """Process an image and text query using the vision model"""
    # The image_data is already in base64 from the client
    # Extract the base64 part if it includes the data URL prefix
    if ',' in image_data:
        base64_image = image_data.split(',', 1)[1]
    else:
        base64_image = image_data

    # Create a fresh conversation for the vision model without system message
    vision_messages = [
        {
            "role": "user", 
            "content": [
                {"type": "text", "text": transcription},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                    },
                },
            ]
        }
    ]

    # Use vision model for image + text 
    completion = client.chat.completions.create(
        # Required parameters
        messages=vision_messages,
        model="llama-3.2-11b-vision-preview",
        
        # Optional parameters
        temperature=0.5,
        max_completion_tokens=1024,
        top_p=1,
        stop=None,
        stream=False,
    )

    # Extract and return vision model response
    return completion.choices[0].message.content

if __name__ == "__main__":
    audio_path = "example_audio.wav"  # replace with actual audio file
    transcribe_audio(audio_path)