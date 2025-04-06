
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import tempfile
import uuid
import base64
import json
from groq_transcribe import transcribe_audio, get_vision_response
from groq_llama import get_llama_response
from google_llm import call_google_llm
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    print("Headers:", request.headers)
    print("Form keys:", request.form.keys())
    print("Files:", request.files)
    print("✅ Hit /transcribe route")
    print("➡️ request.files:", request.files)

    if 'audio' not in request.files:
        print("❌ No audio file provided")
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']

    temp_dir = tempfile.gettempdir()
    temp_filename = f"{uuid.uuid4()}.wav"
    temp_path = os.path.join(temp_dir, temp_filename)
    audio_file.save(temp_path)

    try:
        transcript = transcribe_audio(temp_path)
        print(f"📝 Transcript: {transcript}")
        socketio.emit('transcription_result', {'text': transcript, 'type': 'user'})

        has_image = request.form.get('has_image') == 'true'
        ai_response = ""

        if has_image and 'image_data' in request.form:
            image_data = request.form.get('image_data')
            ai_response = get_vision_response(transcript, image_data)
        else:
            llama_response = get_llama_response(transcript)
            tool_prompt = f"The assistant said: '{llama_response}'. What product would they be referring to if this were a flower recommendation assistant?"
            try:
                google_response = call_google_llm(tool_prompt)
                ai_response = f"{llama_response}\n\nSuggested Product (Google AI): {google_response}"
            except Exception as e:
                ai_response = f"{llama_response}\n\n(Google API call failed: {e})"

        print(f"🤖 AI response: {ai_response}")
        socketio.emit('transcription_result', {'text': ai_response, 'type': 'assistant'})
        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"🔥 Transcription error: {str(e)}")
