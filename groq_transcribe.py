
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

def get_vision_response(transcription, current_image_data, image_history=None):
    """Process an image and text query using the vision model with image history context"""
    # Clean up image_history to use only the most recent 3 images
    if image_history and len(image_history) > 3:
        image_history = image_history[:3]
    
    # Create messages array starting with a system message
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that analyzes images and responds to user queries. Consider all images provided in the conversation when answering."
        }
    ]
    
    # Process the current image data
    if ',' in current_image_data:
        current_base64_image = current_image_data.split(',', 1)[1]
    else:
        current_base64_image = current_image_data
    
    # Add previous images as separate messages to maintain context
    if image_history and len(image_history) > 0:
        for i, prev_img in enumerate(image_history):
            # Skip if this is the same as current image
            if prev_img == current_image_data:
                continue
                
            # Clean the image data
            if ',' in prev_img:
                prev_base64_image = prev_img.split(',', 1)[1]
            else:
                prev_base64_image = prev_img
                
            # Add previous image as a separate message
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": f"This is a previous image ({i+1}) I showed you:"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{prev_base64_image}",
                        }
                    }
                ]
            })
            
            # Add a simple acknowledgment from the assistant
            messages.append({
                "role": "assistant",
                "content": f"I see this previous image ({i+1}). I'll remember this context."
            })
    
    # Add the current user message with current image and transcription
    messages.append({
        "role": "user", 
        "content": [
            {"type": "text", "text": transcription},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{current_base64_image}",
                },
            }
        ]
    })

    try:
        # Use vision model for image + text
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=messages,
            temperature=0.7,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )
        
        # Extract and return vision model response
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Vision API error: {str(e)}")
        # Try with meta-llama model as a backup
        try:
            completion = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=messages,
                temperature=0.7,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
                stop=None,
            )
            return completion.choices[0].message.content
        except Exception as backup_error:
            print(f"Backup model error: {str(backup_error)}")
            raise

if __name__ == "__main__":
    audio_path = "example_audio.wav"  # replace with actual audio file
    transcribe_audio(audio_path)
