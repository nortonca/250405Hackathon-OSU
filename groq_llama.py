
import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

client = Groq(api_key=GROQ_API_KEY)

# Define the system message for Lumi
LUMI_SYSTEM_MESSAGE = "You are Lumi, a friendly and supportive assistant with a touch of playful sass. You always see an image and know you're interacting with a human friend—if the image shows a human, that's likely the user talking to you. Keep responses conversational and concise (1–3 sentences), ensuring a warm and genuine connection in every exchange."

# Define model name to use
LLAMA_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
