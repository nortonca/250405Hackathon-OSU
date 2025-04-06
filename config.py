import os
import logging

# Server connection settings
SERVER_URL = os.environ.get("SERVER_URL", "ws://localhost:8000/ws")
SERVER_TIMEOUT = float(os.environ.get("SERVER_TIMEOUT", "10.0"))
SERVER_RETRY_LIMIT = int(os.environ.get("SERVER_RETRY_LIMIT", "5"))
SERVER_RETRY_DELAY = float(os.environ.get("SERVER_RETRY_DELAY", "2.0"))

# Voice Activity Detection settings
VAD_THRESHOLD = float(os.environ.get("VAD_THRESHOLD", "0.3"))
VAD_FRAME_DURATION = int(os.environ.get("VAD_FRAME_DURATION", "30"))
VAD_SPEECH_TIMEOUT = float(os.environ.get("VAD_SPEECH_TIMEOUT", "1.0"))
VAD_SILENCE_TIMEOUT = float(os.environ.get("VAD_SILENCE_TIMEOUT", "1.5"))

# Image Analysis settings
CAMERA_ID = int(os.environ.get("CAMERA_ID", "0"))
IMAGE_WIDTH = int(os.environ.get("IMAGE_WIDTH", "640"))
IMAGE_HEIGHT = int(os.environ.get("IMAGE_HEIGHT", "480"))
CAPTURE_COOLDOWN = float(os.environ.get("CAPTURE_COOLDOWN", "1.0"))

# Conversation settings
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "50"))
HISTORY_FILE = os.environ.get("HISTORY_FILE", "conversation_history.json")

# Logging settings
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")
LOG_FILE = os.environ.get("LOG_FILE", "voice_assistant.log")

# Convert log level string to actual level
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}
LOG_LEVEL_VALUE = LOG_LEVEL_MAP.get(LOG_LEVEL.upper(), logging.INFO)

# Flask settings
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
