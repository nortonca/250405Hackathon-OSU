
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import tempfile
import uuid
import json
import logging
import time
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

# Performance metrics tracking
request_metrics = {
    'count': 0,
    'total_time': 0,
    'transcription_time': 0,
    'response_time': 0,
    'max_time': 0,
    'min_time': float('inf')
}

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
    # Track overall request time
    request_start_time = time.time()
    
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']

    # Save the uploaded file to a temporary location
    temp_dir = tempfile.gettempdir()
    temp_filename = f"{uuid.uuid4()}.wav"
    temp_path = os.path.join(temp_dir, temp_filename)

    audio_file.save(temp_path)
    file_size = os.path.getsize(temp_path) / 1024  # Size in KB
    logger.debug(f"Audio file saved: {file_size:.2f} KB")

    try:
        # Start with a progress update to client to show we're processing
        socketio.emit('processing_status', {'status': 'transcribing'})
        
        # 1. Transcribe audio with performance tracking
        logger.info(f"Transcribing audio from {temp_path}")
        transcription_start = time.time()
        transcript = transcribe_audio(temp_path)
        transcription_time = time.time() - transcription_start
        logger.info(f"Transcription completed in {transcription_time:.2f}s: '{transcript}'")
        
        # Update transcription metrics
        request_metrics['transcription_time'] += transcription_time
        
        # 2. Get conversation history from client if available
        conversation_history = []
        if 'conversation_history' in request.form:
            try:
                history_parse_start = time.time()
                conversation_history = json.loads(request.form.get('conversation_history'))
                logger.debug(f"Parsed conversation history with {len(conversation_history)} messages in {time.time() - history_parse_start:.4f}s")
            except Exception as e:
                logger.error(f"Error parsing conversation history: {str(e)}")
        
        # 3. Process with the unified AI response function
        socketio.emit('processing_status', {'status': 'generating_response'})
        has_image = request.form.get('has_image') == 'true'
        image_data = request.form.get('image_data') if has_image and 'image_data' in request.form else None
        if has_image and image_data:
            # Log only truncated version of image data for debugging
            truncated_data = image_data[:50] + "..." if image_data else "None"
            logger.info(f"Processing request - Has image: {has_image}, image_data_length: {len(image_data)}, preview: {truncated_data}")
        else:
            logger.info(f"Processing request - Has image: {has_image}")
        
        # 4. Get AI response with performance tracking
        logger.debug("Calling Groq API for AI response")
        response_start = time.time()
        ai_response = get_ai_response(transcript, image_data, conversation_history)
        response_time = time.time() - response_start
        logger.info(f"AI response generated in {response_time:.2f}s")
        
        # Update response metrics
        request_metrics['response_time'] += response_time
        
        # 5. Send combined results to client in a single update
        socketio.emit('conversation_update', {
            'user_message': {'text': transcript, 'type': 'user'},
            'ai_response': {'text': ai_response, 'type': 'assistant'}
        })
        logger.debug("Sent complete conversation update to client")
        
        # 6. Calculate and log total processing time
        total_time = time.time() - request_start_time
        
        # Update overall metrics
        request_metrics['count'] += 1
        request_metrics['total_time'] += total_time
        request_metrics['max_time'] = max(request_metrics['max_time'], total_time)
        request_metrics['min_time'] = min(request_metrics['min_time'], total_time)
        avg_time = request_metrics['total_time'] / request_metrics['count']
        
        logger.info(f"Request completed in {total_time:.2f}s (avg: {avg_time:.2f}s)")
        logger.debug(f"Performance metrics: {request_metrics}")
        
        # 7. Return success with timing information
        return jsonify({
            'success': True,
            'transcript': transcript,
            'response': ai_response,
            'timing': {
                'total_seconds': round(total_time, 2),
                'transcription_seconds': round(transcription_time, 2),
                'response_seconds': round(response_time, 2)
            }
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

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Return performance metrics for monitoring"""
    from groq_service import cache_metrics

    # Calculate derived metrics for requests
    metrics = dict(request_metrics)
    
    if metrics['count'] > 0:
        metrics['avg_time'] = round(metrics['total_time'] / metrics['count'], 3)
        metrics['avg_transcription'] = round(metrics['transcription_time'] / metrics['count'], 3)
        metrics['avg_response'] = round(metrics['response_time'] / metrics['count'], 3)
        metrics['min_time'] = round(metrics['min_time'], 3) if metrics['min_time'] != float('inf') else 0
        metrics['max_time'] = round(metrics['max_time'], 3)
    else:
        metrics['avg_time'] = 0
        metrics['avg_transcription'] = 0
        metrics['avg_response'] = 0
        metrics['min_time'] = 0
    
    # Add cache metrics
    metrics['cache'] = dict(cache_metrics)
    
    # Calculate cache hit rate
    total_cache_requests = cache_metrics['hits'] + cache_metrics['misses']
    if total_cache_requests > 0:
        hit_rate = (cache_metrics['hits'] / total_cache_requests) * 100
        metrics['cache']['hit_rate'] = round(hit_rate, 1)
    else:
        metrics['cache']['hit_rate'] = 0
    
    # Round saved time
    metrics['cache']['saved_time'] = round(cache_metrics['saved_time'], 2)
    
    return jsonify(metrics)

if __name__ == '__main__':
    logger.info("Starting Lumi Voice AI Assistant web server")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=True, log_output=True)
