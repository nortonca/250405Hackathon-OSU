import { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Camera, CameraOff } from 'lucide-react';
import { AudioProcessor } from './lib/AudioProcessor';
import { CameraManager } from './lib/CameraManager';

interface Transcript {
  text: string;
  type: 'user' | 'ai';
  metadata?: any;
}

function App() {
  const [isListening, setIsListening] = useState(false);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [status, setStatus] = useState('Ready to detect voice');
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const startVoiceDetection = async () => {
    try {
      const success = await AudioProcessor.initVAD({
        onSpeechStart: () => {
          setStatus('Speech detected! Recording...');
          if (isCameraOn && videoRef.current && canvasRef.current) {
            CameraManager.captureFrame();
          }
        },
        onSpeechEnd: async (audio) => {
          setStatus('Processing speech...');
          try {
            const imageData = isCameraOn ? CameraManager.captureFrame() : null;
            const result = await AudioProcessor.processPipeline(audio, imageData);
            
            if (result.transcript) {
              setTranscripts(prev => [...prev, 
                { 
                  text: result.transcript, 
                  type: 'user',
                  metadata: result.metadata 
                },
                {
                  text: result.aiResponse || 'No response from AI',
                  type: 'ai'
                }
              ]);
            }

            setStatus('Ready to detect voice');
          } catch (error) {
            console.error('Error processing audio:', error);
            setStatus('Error processing speech. Please try again.');
          }
        },
        onError: (error) => {
          console.error('VAD error:', error);
          setStatus('Error with voice detection. Please try again.');
          setIsListening(false);
        }
      });

      if (success) {
        AudioProcessor.startListening();
        setIsListening(true);
        setStatus('Listening for speech...');
      }
    } catch (error) {
      console.error('Error initializing voice detection:', error);
      setStatus('Failed to initialize voice detection');
      setIsListening(false);
    }
  };

  const stopVoiceDetection = () => {
    AudioProcessor.stopListening();
    setIsListening(false);
    setStatus('Voice detection stopped');
  };

  const toggleCamera = async () => {
    if (!isCameraOn) {
      try {
        if (videoRef.current && canvasRef.current) {
          CameraManager.init(videoRef.current, canvasRef.current);
          const success = await CameraManager.startCamera();
          if (success) {
            setIsCameraOn(true);
          } else {
            setStatus('Failed to start camera');
          }
        }
      } catch (err) {
        setStatus('Camera access denied');
        console.error('Camera error:', err);
      }
    } else {
      CameraManager.stopCamera();
      setIsCameraOn(false);
    }
  };

  useEffect(() => {
    // Auto-start camera if permissions are already granted
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        stream.getTracks().forEach(track => track.stop());
        toggleCamera();
      })
      .catch(err => console.log("Camera requires manual activation", err));
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-center text-blue-600">
            Lumi - Voice AI Assistant
          </h1>
          <p className="text-center text-gray-600 mt-2">
            Speak to interact with Lumi, your friendly AI assistant
          </p>
        </header>

        <main className="bg-white rounded-lg shadow-md p-6 max-w-lg mx-auto">
          <div className={`mb-4 p-3 rounded-lg text-center ${
            status.includes('Error') ? 'bg-red-100 text-red-700' : 'bg-gray-100'
          }`}>
            {status}
          </div>

          <div className="flex flex-col space-y-4">
            <button
              onClick={isListening ? stopVoiceDetection : startVoiceDetection}
              className={`flex items-center justify-center gap-2 px-4 py-2 rounded transition ${
                isListening 
                  ? 'bg-red-500 hover:bg-red-600' 
                  : 'bg-blue-500 hover:bg-blue-600'
              } text-white`}
            >
              {isListening ? (
                <>
                  <MicOff size={20} />
                  Stop Listening
                </>
              ) : (
                <>
                  <Mic size={20} />
                  Start Listening
                </>
              )}
            </button>

            <div className="mt-4 p-4 border border-gray-200 rounded-lg">
              <h3 className="text-lg font-medium mb-2">Camera Feed</h3>
              <p className="text-sm text-gray-500 mb-3">
                Your camera will automatically capture when you speak
              </p>

              <div className="flex flex-col items-center justify-center w-full">
                <div className="relative w-full">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    className="w-full rounded-lg bg-black"
                  />
                  <div className="absolute bottom-2 right-2 bg-gray-800 text-white text-xs px-2 py-1 rounded-full opacity-75">
                    {isCameraOn ? 'Camera active' : 'Camera inactive'}
                  </div>
                </div>

                <button
                  onClick={toggleCamera}
                  className="mt-2 flex items-center gap-2 px-3 py-1 rounded text-sm text-white transition-colors duration-200 ease-in-out bg-blue-500 hover:bg-blue-600"
                >
                  {isCameraOn ? (
                    <>
                      <CameraOff size={16} />
                      Stop Camera
                    </>
                  ) : (
                    <>
                      <Camera size={16} />
                      Start Camera
                    </>
                  )}
                </button>
              </div>

              <div className="mt-4">
                <p className="text-sm font-medium mb-2">Last Captured Frame:</p>
                <canvas
                  ref={canvasRef}
                  className="max-h-48 rounded-lg mx-auto object-contain border border-gray-300"
                />
              </div>
            </div>
          </div>

          <div className="mt-6 h-64 overflow-y-auto border border-gray-200 rounded p-4">
            {transcripts.length === 0 ? (
              <div className="text-gray-500 text-center">
                Transcriptions will appear here
              </div>
            ) : (
              transcripts.map((transcript, index) => (
                <div
                  key={index}
                  className={`mb-2 p-2 rounded ${
                    transcript.type === 'user' 
                      ? 'bg-blue-50 self-end' 
                      : 'bg-purple-50 self-start'
                  }`}
                >
                  <span className="font-semibold">
                    {transcript.type === 'user' ? 'You' : 'Lumi'}:
                  </span>{' '}
                  {transcript.text}
                  {transcript.metadata && (
                    <div className="text-xs text-gray-500 mt-1">
                      Quality: {Math.round((1 + transcript.metadata.avg_logprob) * 100)}%
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </main>

        <footer className="mt-8 text-center text-gray-500 text-sm">
          <p>© 2025 - Lumi Voice AI Assistant</p>
        </footer>
      </div>
    </div>
  );
}

export default App;