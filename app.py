
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import tempfile
import uuid
from groq_transcribe import transcribe_audio, get_ai_response

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
socketio = SocketIO(app, cors_allowed_origins="*")

# Keep track of the latest image path for context
latest_image_path = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    global latest_image_path
    
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    
    # Save the uploaded file to a temporary location
    temp_dir = tempfile.gettempdir()
    temp_filename = f"{uuid.uuid4()}.wav"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    audio_file.save(temp_path)
    
    try:
        # Call the transcription function
        transcript = transcribe_audio(temp_path)
        
        # Broadcast the transcription result to all connected clients
        socketio.emit('transcription_result', {'text': transcript, 'type': 'user'})
        
        # Get AI response and broadcast it, passing the latest image if available
        ai_response = get_ai_response(transcript, latest_image_path)
        socketio.emit('transcription_result', {'text': ai_response, 'type': 'assistant'})
        
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/upload-image', methods=['POST'])
def upload_image():
    global latest_image_path
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    image_file = request.files['image']
    
    if image_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if image_file:
        filename = f"{uuid.uuid4()}_{image_file.filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(file_path)
        latest_image_path = file_path
        
        # Notify all clients that an image has been uploaded
        socketio.emit('image_uploaded', {
            'image_url': f'/{file_path}',
            'message': 'Image uploaded successfully'
        })
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': file_path
        }), 200
    
    return jsonify({'error': 'Failed to upload image'}), 500

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
