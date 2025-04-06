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