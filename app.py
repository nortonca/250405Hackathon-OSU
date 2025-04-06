from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO, emit
import os
from werkzeug.utils import secure_filename
from groq_transcribe import transcribe_audio
from google_llm import call_google_llm
from recommend_flower import recommend_flower
from eleven_tts import synthesize_speech

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def handle_transcribe():
    print("✅ Hit /transcribe route")

    if 'audio' not in request.files:
        print("❌ No audio file part in the request")
        return "No audio file", 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        print("❌ Empty filename")
        return "Empty filename", 400

    filename = secure_filename("speech.wav")
    filepath = os.path.join("static", filename)
    audio_file.save(filepath)

    print(f"➡️ request.files: {request.files}")
    transcript = transcribe_audio(filepath)
    print(f"📝 Transcript:  {transcript}")

    response = call_google_llm(transcript)
    print(f"🤖 AI response: {response}")

    flower = recommend_flower(transcript)
    response += f"\n\nSuggested Product (Google AI): {flower}"

    tts_result = synthesize_speech(response)
    if tts_result:
        print("🔊 TTS audio generated successfully.")
    else:
        print("⚠️ Skipped TTS or failed to generate audio.")

    socketio.emit('response', {
        'transcript': transcript,
        'response': response
    })

    return "OK", 200

@socketio.on('connect')
def handle_connect():
    print("⚡ Client connected")
    emit('response', {'data': 'Connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print("🔌 Client disconnected")

# Ensure output.mp3 file exists to avoid 404 errors
if not os.path.exists("static"):
    os.makedirs("static", exist_ok=True)

if not os.path.exists("static/output.mp3"):
    open("static/output.mp3", "wb").close()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')

