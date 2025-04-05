from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import tempfile
import uuid
from groq_transcribe import transcribe_audio

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe-page')
def transcribe_page():
    return render_template('transcribe.html')

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
        # Call the transcription function
        transcript = transcribe_audio(temp_path)
        
        # Broadcast the result to all connected clients
        socketio.emit('transcription_result', {'text': transcript})
        
        return jsonify({'text': transcript}), 200
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('response', {'data': 'Connected'})

@socketio.on('message')
def handle_message(data):
    print('received message: ' + str(data))
    emit('response', {'data': f'Server received: {data}'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000) 