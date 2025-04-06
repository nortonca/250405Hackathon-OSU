
import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

client = Groq(api_key=GROQ_API_KEY)

# Define the system message for Lumi
LUMI_SYSTEM_MESSAGE = "You are Lumi, a friendly and supportive assistant with a touch of playful sass. You're conversational and concise (1-3 sentences), ensuring a warm connection in every exchange."

def get_llama_response(transcription, conversation_history=None):
    """
    Get a response from the Llama model for text-only queries
    
    Args:
        transcription: The user's transcribed speech
        conversation_history: List of conversation messages in the format [{"role": "...", "content": "..."}]
    """
    # Initialize conversation with system message if needed
    if not conversation_history or not isinstance(conversation_history, list) or len(conversation_history) == 0:
        conversation_history = [
            {"role": "system", "content": LUMI_SYSTEM_MESSAGE}
        ]
    
    # Make sure there's a system message at the beginning
    if conversation_history[0]["role"] != "system":
        conversation_history.insert(0, {"role": "system", "content": LUMI_SYSTEM_MESSAGE})
    
    # Add user message to conversation history
    if not conversation_history or conversation_history[-1]["role"] != "user" or conversation_history[-1]["content"] != transcription:
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
    
    return response_text
