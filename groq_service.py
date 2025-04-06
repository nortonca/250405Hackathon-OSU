import os
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

client = Groq(api_key=GROQ_API_KEY)

# Define a single system prompt to be used for all interactions
LUMI_SYSTEM_PROMPT = "You are Lumi, a friendly and supportive assistant with a touch of playful sass. You always see an image and know you're interacting with a human friend—if the image shows a human, that's likely the user talking to you. Keep responses conversational and concise (1–3 sentences), ensuring a warm and genuine connection in every exchange."

def transcribe_audio(file_path):
    """Transcribe audio to text using Groq's API"""
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=audio_file,
            model="distil-whisper-large-v3-en"
        )
        return response.text

def get_ai_response(transcription, image_data=None, conversation_history=None):
    """
    Get a response from the AI model using either text-only or image+text
    
    Args:
        transcription: The user's transcribed speech
        image_data: Optional base64 image data for vision model
        conversation_history: Optional conversation history
    """
    # Initialize conversation with system message if needed
    if not conversation_history or not isinstance(conversation_history, list) or len(conversation_history) == 0:
        conversation_history = [
            {"role": "system", "content": LUMI_SYSTEM_PROMPT}
        ]
    
    # Make sure there's a system message at the beginning
    if conversation_history[0]["role"] != "system":
        conversation_history.insert(0, {"role": "system", "content": LUMI_SYSTEM_PROMPT})
    
    # Create appropriate message format based on whether we have an image
    # Use a single unified model approach
    model = "meta-llama/llama-4-scout-17b-16e-instruct"  # Using vision-capable model for all interactions

    if image_data:
        # Extract the base64 part if it includes the data URL prefix
        if ',' in image_data:
            base64_image = image_data.split(',', 1)[1]
        else:
            base64_image = image_data
        
        # Create user message with image and text
        user_message = {
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
        
        # Start with system prompt and add user message
        messages = [
            {"role": "system", "content": LUMI_SYSTEM_PROMPT},
            user_message
        ]
        
        # Add a limited amount of previous conversation for context if available
        # Take only the last few exchanges to keep context manageable
        if conversation_history and len(conversation_history) > 2:
            # Extract only assistant and user messages (skip system)
            prev_messages = [msg for msg in conversation_history[1:] if msg["role"] in ["user", "assistant"]]
            
            # Take last 6 messages maximum (3 exchanges) before current
            prev_messages = prev_messages[-6:] if len(prev_messages) > 6 else prev_messages
            
            # Insert previous messages before current user message
            messages = [messages[0]] + prev_messages + [user_message]
    else:
        # For text-only, add the user's transcription to the conversation history
        if not conversation_history or conversation_history[-1]["role"] != "user" or conversation_history[-1]["content"] != transcription:
            conversation_history.append({"role": "user", "content": transcription})
            
        messages = conversation_history
    
    # Get response from Groq API
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    
    # Extract response text
    response_text = completion.choices[0].message.content
    
    return response_text