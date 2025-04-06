
import os
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

client = Groq(api_key=GROQ_API_KEY)

# Import system message from llama module to maintain consistency
from groq_llama import LUMI_SYSTEM_MESSAGE, LLAMA_MODEL

def transcribe_audio(file_path):
    """Transcribe audio to text using Groq's API"""
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=audio_file,
            model="distil-whisper-large-v3-en"
        )
        return response.text

def get_vision_response(transcription, image_data, conversation_history=None):
    """
    Process an image and text query using the Llama 4 Scout vision model
    
    Args:
        transcription: The user's transcribed speech
        image_data: Base64 encoded image data
        conversation_history: Optional conversation history
    """
    # Extract the base64 part if it includes the data URL prefix
    if ',' in image_data:
        base64_image = image_data.split(',', 1)[1]
    else:
        base64_image = image_data
    
    # Default message structure with system message
    messages = [
        {
            "role": "system",
            "content": LUMI_SYSTEM_MESSAGE
        }
    ]
    
    # Add conversation history if available, skipping system message if exists
    if conversation_history and isinstance(conversation_history, list):
        start_idx = 1 if conversation_history and conversation_history[0]["role"] == "system" else 0
        for msg in conversation_history[start_idx:]:
            messages.append(msg)
    
    # Add the current user message with image directly
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": transcription
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
        ]
    })
    
    # Use Llama 4 Scout model for image + text
    completion = client.chat.completions.create(
        model=LLAMA_MODEL,
        messages=messages,
        temperature=1,
        max_completion_tokens=250,
        top_p=1,
        stream=False,
        stop=None,
    )
    
    # Extract and return vision model response
    return completion.choices[0].message.content
