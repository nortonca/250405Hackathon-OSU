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

def get_vision_response(transcription, image_data, image_history=None):
    """Process an image and text query using the vision model"""
    # The image_data is already in base64 from the client
    # Extract the base64 part if it includes the data URL prefix
    if ',' in image_data:
        base64_image = image_data.split(',', 1)[1]
    else:
        base64_image = image_data
    
    # Create messages for the vision model (without system message since it's incompatible)
    vision_messages = []
    
    # Add previous image history if available
    if image_history and isinstance(image_history, list):
        print(f"Received {len(image_history)} images in history")
        
        valid_images = 0
        # Process image history - add previous exchanges that contain images
        for prev_msg in image_history:
            if prev_msg.get("role") in ["user", "assistant"]:
                # For user messages with images
                if prev_msg["role"] == "user" and isinstance(prev_msg.get("content"), list):
                    msg_content = []
                    has_image = False
                    
                    # Process each content item
                    for content_item in prev_msg["content"]:
                        if content_item.get("type") == "text":
                            msg_content.append({"type": "text", "text": content_item["text"]})
                        elif content_item.get("type") == "image_url" and "image_url" in content_item:
                            has_image = True
                            msg_content.append({
                                "type": "image_url",
                                "image_url": content_item["image_url"]
                            })
                    
                    if has_image:
                        valid_images += 1
                        vision_messages.append({
                            "role": "user",
                            "content": msg_content
                        })
                
                # For assistant responses
                elif prev_msg["role"] == "assistant" and prev_msg.get("content"):
                    vision_messages.append({
                        "role": "assistant",
                        "content": prev_msg["content"]
                    })
        
        print(f"Valid images in history: {valid_images}")
    
    # Add current message
    vision_messages.append({
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
    })

    try:
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
    except Exception as e:
        print(f"Vision API error: {e}")
        # Fallback to simpler request if history causes issues
        if vision_messages and len(vision_messages) > 1:
            # Try again with just the current message
            return get_vision_response(transcription, image_data, None)
        else:
            raise e

if __name__ == "__main__":
    audio_path = "example_audio.wav"  # replace with actual audio file
    transcribe_audio(audio_path)