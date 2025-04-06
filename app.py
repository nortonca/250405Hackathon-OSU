
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import tempfile
import uuid
import json
import logging
from groq_service import transcribe_audio, get_ai_response

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
socketio = SocketIO(app, cors_allowed_origins="*")

logger.info("Application initialized with Lumi Voice AI Assistant")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']

    # Save the uploaded file to a temporary location
    temp_dir = tempfile.gettempdir()
    temp_filename = f"{uuid.uuid4()}.wav"
    temp_path = os.path.join(temp_dir, temp_filename)

    audio_file.save(temp_path)

    try:
        # 1. Transcribe audio
        logger.info(f"Transcribing audio from {temp_path}")
        transcript = transcribe_audio(temp_path)
        logger.info(f"Transcription successful: '{transcript}'")
        
        # 2. Send transcription to client
        socketio.emit('transcription_result', {'text': transcript, 'type': 'user'})
        logger.debug("Sent user transcription to client")
        
        # 3. Get conversation history from client if available
        conversation_history = []
        if 'conversation_history' in request.form:
            try:
                conversation_history = json.loads(request.form.get('conversation_history'))
                logger.debug(f"Parsed conversation history with {len(conversation_history)} messages")
            except Exception as e:
                logger.error(f"Error parsing conversation history: {str(e)}")
        
        # 4. Process with the unified AI response function
        has_image = request.form.get('has_image') == 'true'
        image_data = request.form.get('image_data') if has_image and 'image_data' in request.form else None
        logger.info(f"Processing request - Has image: {has_image}")
        
        # Get AI response with optional image and conversation history
        logger.debug("Calling Groq API for AI response")
        ai_response = get_ai_response(transcript, image_data, conversation_history)
        logger.info("Successfully received AI response")
        
        # 5. Send AI response to client
        socketio.emit('transcription_result', {'text': ai_response, 'type': 'assistant'})
        logger.debug("Sent AI response to client")
        
        # 6. Return success to complete the request
        return jsonify({
            'success': True,
            'transcript': transcript,
            'response': ai_response
        }), 200
    except Exception as e:
        logger.error(f"Transcription pipeline error: {str(e)}", exc_info=True)
        socketio.emit('transcription_error', {'error': str(e)})
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('local_image_ready')
def handle_local_image_ready(ready):
    logger.info(f'Client has local image ready: {ready}')

if __name__ == '__main__':
    logger.info("Starting Lumi Voice AI Assistant web server")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=True, log_output=True)
