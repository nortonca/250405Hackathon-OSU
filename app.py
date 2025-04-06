
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import tempfile
import uuid
import base64
import json
from groq_transcribe import transcribe_audio, get_vision_response
from groq_llama import get_llama_response

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
socketio = SocketIO(app, cors_allowed_origins="*")

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
        transcript = transcribe_audio(temp_path)
        
        # 2. Send transcription to client
        socketio.emit('transcription_result', {'text': transcript, 'type': 'user'})
        
        # 3. Get conversation history from client if available
        conversation_history = []
        if 'conversation_history' in request.form:
            try:
                conversation_history = json.loads(request.form.get('conversation_history'))
            except Exception as e:
                print(f"Error parsing conversation history: {str(e)}")
        
        # 4. Process with appropriate model
        has_image = request.form.get('has_image') == 'true'
        
        if has_image and 'image_data' in request.form:
            # Vision model path with client-provided image
            image_data = request.form.get('image_data')
            
            # Create image history from conversation history
            image_history = []
            
            # Process conversation history to extract image messages
            for msg in conversation_history:
                # Skip system messages for vision model
                if msg.get('role') == 'system':
                    continue
                
                # For user messages that might contain images
                if msg.get('role') == 'user' and msg.get('has_image', False):
                    # Create a proper content structure for vision API
                    content = [{"type": "text", "text": msg.get('content', '')}]
                    
                    # Add image if available
                    if msg.get('image_data'):
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{msg.get('image_data').split(',', 1)[1] if ',' in msg.get('image_data', '') else msg.get('image_data', '')}"
                            }
                        })
                    
                    # Add to image history
                    image_history.append({
                        "role": "user",
                        "content": content
                    })
                
                # For assistant responses
                elif msg.get('role') == 'assistant':
                    image_history.append(msg)
            
            # Get response using vision model with image history
            ai_response = get_vision_response(transcript, image_data, image_history)
        else:
            # Regular text-only conversation with Llama and client-provided history
            ai_response = get_llama_response(transcript, conversation_history)
        
        # 5. Send AI response to client
        socketio.emit('transcription_result', {'text': ai_response, 'type': 'assistant'})
        
        # 6. Return success to complete the request
        return jsonify({
            'success': True,
            'transcript': transcript,
            'response': ai_response
        }), 200
    except Exception as e:
        print(f"Transcription pipeline error: {str(e)}")
        socketio.emit('transcription_error', {'error': str(e)})
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('local_image_ready')
def handle_local_image_ready(ready):
    print('Client has local image ready:', ready)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
