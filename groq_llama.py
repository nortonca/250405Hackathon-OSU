
import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

client = Groq(api_key=GROQ_API_KEY)

def get_llama_response(transcription, conversation_history=None):
    """
    Get a response from the Llama model for text-only queries using provided conversation history
    
    Args:
        transcription: The user's transcribed speech
        conversation_history: List of conversation messages in the format [{"role": "...", "content": "..."}]
    """
    # If no history is provided, use a default system message
    if not conversation_history or not isinstance(conversation_history, list) or len(conversation_history) == 0:
        conversation_history = [
            {"role": "system", "content": "You are a helpful assistant responding to voice transcriptions and image analysis. Keep responses concise and natural."}
        ]
    
    # Make sure there's a system message at the beginning
    if conversation_history[0]["role"] != "system":
        conversation_history.insert(0, {"role": "system", "content": "You are a helpful assistant responding to voice transcriptions and image analysis. Keep responses concise and natural."})
    
    # Add user message to conversation history if it's not already there
    if not conversation_history or conversation_history[-1]["role"] != "user" or conversation_history[-1]["content"] != transcription:
        conversation_history.append({"role": "user", "content": transcription})
    
    # Get response from Groq API
    completion = client.chat.completions.create(
        # Required parameters
        messages=conversation_history,
        model="llama-3.3-70b-versatile",
        
        # Optional parameters
        temperature=0.5,
        max_completion_tokens=1024,
        top_p=1,
        stop=None,
        stream=False,
    )
    
    # Extract response text
    response_text = completion.choices[0].message.content
    
    return response_text
