from flask import Flask, render_template, request, jsonify
import os
import logging
import threading
from voice_assistant import VoiceAssistant

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Initialize voice assistant
voice_assistant = None
assistant_thread = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_assistant', methods=['POST'])
def start_assistant():
    global voice_assistant, assistant_thread
    
    try:
        if assistant_thread and assistant_thread.is_alive():
            logger.info("Assistant already running")
            return jsonify({"status": "success", "message": "Assistant already running"})
        
        # Create a new voice assistant instance
        voice_assistant = VoiceAssistant()
        
        # Start voice assistant in a separate thread
        assistant_thread = threading.Thread(target=voice_assistant.start)
        assistant_thread.daemon = True
        assistant_thread.start()
        
        logger.info("Voice assistant started successfully")
        return jsonify({"status": "success", "message": "Assistant started"})
    except Exception as e:
        logger.error(f"Failed to start assistant: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to start: {str(e)}"}), 500

@app.route('/stop_assistant', methods=['POST'])
def stop_assistant():
    global voice_assistant
    
    try:
        if voice_assistant:
            voice_assistant.stop()
            logger.info("Voice assistant stopped")
            return jsonify({"status": "success", "message": "Assistant stopped"})
        else:
            logger.warning("No active assistant to stop")
            return jsonify({"status": "warning", "message": "No active assistant"}), 404
    except Exception as e:
        logger.error(f"Failed to stop assistant: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to stop: {str(e)}"}), 500

@app.route('/get_conversation', methods=['GET'])
def get_conversation():
    global voice_assistant
    
    try:
        if voice_assistant:
            conversation = voice_assistant.get_conversation_history()
            return jsonify({"status": "success", "conversation": conversation})
        else:
            return jsonify({"status": "warning", "message": "No active assistant"}), 404
    except Exception as e:
        logger.error(f"Failed to get conversation: {str(e)}")
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

@app.route('/get_status', methods=['GET'])
def get_status():
    global voice_assistant, assistant_thread
    
    if voice_assistant and assistant_thread and assistant_thread.is_alive():
        return jsonify({
            "status": "running",
            "server_connected": voice_assistant.is_server_connected(),
            "vad_state": voice_assistant.get_vad_state(),
            "recent_events": voice_assistant.get_recent_events()
        })
    else:
        return jsonify({"status": "stopped"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
