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
    # Process the current image
    # Extract the base64 part if it includes the data URL prefix
    if ',' in current_image_data:
        current_base64_image = current_image_data.split(',', 1)[1]
    else:
        current_base64_image = current_image_data

    # Create content array for user message
    user_content = [
        {"type": "text", "text": transcription},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{current_base64_image}",
            },
        }
    ]
    
    # Add system message with context about image history
    vision_messages = []
    
    # Create a system message that explains the context of multiple images
    if image_history and len(image_history) > 0:
        system_message = {
            "role": "system",
            "content": f"You are analyzing a conversation with {len(image_history) + 1} images. "
                       f"The user has shared {len(image_history)} previous images and is now showing you a new image. "
                       f"Consider both the current image and context from previous images when responding."
        }
        vision_messages.append(system_message)
    
    # Add previous images (oldest to newest) to provide context
    if image_history and len(image_history) > 0:
        # Create a context message with previous images
        previous_images_content = [{"type": "text", "text": "Here are my previous images for context:"}]
        
        # Add each previous image
        for i, img in enumerate(image_history):
            if img.get('data'):
                img_data = img['data']
                # Extract base64 if needed
                if ',' in img_data:
                    img_base64 = img_data.split(',', 1)[1]
                else:
                    img_base64 = img_data
                
                previous_images_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}",
                    }
                })
        
        # Add context message with previous images
        vision_messages.append({
            "role": "user",
            "content": previous_images_content
        })
        
        # Add assistant acknowledgment
        vision_messages.append({
            "role": "assistant",
            "content": "I've received your previous images and will keep them in mind when analyzing your new image and question."
        })

    # Add current user message with new image
    vision_messages.append({
        "role": "user", 
        "content": user_content
    })

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

    # Extract and return vision model response
    return completion.choices[0].message.content

if __name__ == "__main__":
    audio_path = "example_audio.wav"  # replace with actual audio file
    transcribe_audio(audio_path)