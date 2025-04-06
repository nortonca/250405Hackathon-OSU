
import os
import base64
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

client = Groq(api_key=GROQ_API_KEY)

# Keep track of conversation history
conversation_history = [
    {"role": "system", "content": "You are a helpful assistant responding to voice transcriptions and image analysis. Keep responses concise and natural."}
]

def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=audio_file,
            model="distil-whisper-large-v3-en"
        )
        return response.text

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_ai_response(transcription, image_path=None):
    # Create message content
    if image_path and os.path.exists(image_path):
        # Using the vision model for image analysis - create a fresh conversation without system message
        base64_image = encode_image(image_path)
        
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
            model="llama-3.2-11b-vision-preview",
            messages=vision_messages,
            temperature=0.7,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )
        
        # Add the exchange to conversation history as plain text for future context
        conversation_history.append({"role": "user", "content": transcription + " [Image analysis requested]"})
    else:
        # Regular text-only conversation
        conversation_history.append({"role": "user", "content": transcription})
        
        # Get response from Groq API
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=conversation_history,
            temperature=0.7,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )
    
    # Extract response text
    response_text = completion.choices[0].message.content
    
    # Add assistant response to conversation history
    conversation_history.append({"role": "assistant", "content": response_text})
    
    return response_text

if __name__ == "__main__":
    audio_path = "example_audio.wav"  # replace with actual audio file
    transcribe_audio(audio_path)
