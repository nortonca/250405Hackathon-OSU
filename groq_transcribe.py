
import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

client = Groq(api_key=GROQ_API_KEY)

# Keep track of conversation history
conversation_history = [
    {"role": "system", "content": "You are a helpful assistant responding to voice transcriptions. Keep responses concise and natural."}
]

def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=audio_file,
            model="distil-whisper-large-v3-en"
        )
        return response.text

def get_ai_response(transcription):
    # Add user message to conversation history
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
