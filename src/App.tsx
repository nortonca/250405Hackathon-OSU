import { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Camera, CameraOff, Search, Flower, MessageSquare } from 'lucide-react';
import { AudioProcessor } from './lib/AudioProcessor';
import { CameraManager } from './lib/CameraManager';
import { Modal } from './components/Modal';

interface Transcript {
  text: string;
  type: 'user' | 'ai' | 'tool';
  metadata?: any;
  toolName?: string;
  toolStatus?: 'calling' | 'success' | 'error';
}

function App() {
  const [isListening, setIsListening] = useState(false);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [sendVisualInput, setSendVisualInput] = useState(false);
  const [status, setStatus] = useState('Ready to assist with your floral needs');
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const transcriptContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (transcriptContainerRef.current) {
      transcriptContainerRef.current.scrollTop = transcriptContainerRef.current.scrollHeight;
    }
  }, [transcripts]);

  const startVoiceDetection = async () => {
    try {
      const success = await AudioProcessor.initVAD({
        onSpeechStart: () => {
          setStatus('Listening to your request...');
          if (sendVisualInput && videoRef.current && canvasRef.current) {
            CameraManager.captureFrame();
          }
        },
        onSpeechEnd: async (audio) => {
          setStatus('Processing your request...');
          try {
            const imageData = sendVisualInput ? CameraManager.captureFrame() : null;
            const result = await AudioProcessor.processPipeline(audio, imageData);
            
            if (result.transcript) {
              const newTranscripts: Transcript[] = [
                { 
                  text: result.transcript, 
                  type: 'user',
                  metadata: result.metadata 
                }
              ];

              if (result.toolCalls) {
                result.toolCalls.forEach(toolCall => {
                  newTranscripts.push({
                    text: `Checking ${toolCall.name.replace(/_/g, ' ')}...`,
                    type: 'tool',
                    toolName: toolCall.name,
                    toolStatus: 'calling'
                  });
                  
                  newTranscripts.push({
                    text: toolCall.result,
                    type: 'tool',
                    toolName: toolCall.name,
                    toolStatus: toolCall.isError ? 'error' : 'success'
                  });
                });
              }

              newTranscripts.push({
                text: result.aiResponse || 'I apologize, but I was unable to process your request.',
                type: 'ai'
              });

              setTranscripts(prev => [...prev, ...newTranscripts]);
            }

            setStatus('Ready to assist with your floral needs');
          } catch (error) {
            console.error('Error processing audio:', error);
            setStatus('I apologize, but there was an error processing your request. Please try again.');
          }
        },
        onError: (error) => {
          console.error('VAD error:', error);
          setStatus('There was an issue with voice detection. Please try again.');
          setIsListening(false);
        }
      });

      if (success) {
        AudioProcessor.startListening();
        setIsListening(true);
        setStatus('Listening for your floral request...');
      }
    } catch (error) {
      console.error('Error initializing voice detection:', error);
      setStatus('Unable to start voice detection');
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
            setSendVisualInput(true);
          } else {
            setStatus('Unable to start camera');
          }
        }
      } catch (err) {
        setStatus('Camera access denied');
        console.error('Camera error:', err);
      }
    } else {
      CameraManager.stopCamera();
      setIsCameraOn(false);
      setSendVisualInput(false);
    }
  };

  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        stream.getTracks().forEach(track => track.stop());
        toggleCamera();
      })
      .catch(err => console.log("Camera requires manual activation", err));
  }, []);

  const getToolIcon = (toolName: string) => {
    switch (toolName) {
      case 'product_search':
        return <Flower className="w-4 h-4" />;
      case 'gemini_search':
        return <Search className="w-4 h-4" />;
      case 'show_input_modal':
        return <MessageSquare className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const getToolStatusColor = (status?: 'calling' | 'success' | 'error') => {
    switch (status) {
      case 'calling':
        return 'bg-yellow-50 border-yellow-200';
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'error':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-rose-50 to-white">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-rose-600 mb-2">
            Flora's Flower Shop
          </h1>
          <p className="text-gray-600 text-lg">
            Your personal floral assistant for perfect blooms every time
          </p>
        </header>

        <main className="bg-white rounded-xl shadow-lg p-6 max-w-2xl mx-auto border border-rose-100">
          <div className={`mb-4 p-3 rounded-lg text-center ${
            status.includes('Error') ? 'bg-red-50 text-red-700' : 'bg-rose-50 text-rose-700'
          }`}>
            {status}
          </div>

          <div className="flex flex-col space-y-4">
            <button
              onClick={isListening ? stopVoiceDetection : startVoiceDetection}
              className={`flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition ${
                isListening 
                  ? 'bg-red-500 hover:bg-red-600' 
                  : 'bg-rose-500 hover:bg-rose-600'
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
                  Start Speaking
                </>
              )}
            </button>

            <div className="mt-4 p-4 border border-rose-200 rounded-lg bg-rose-50">
              <h3 className="text-lg font-medium mb-2 text-rose-700">Visual Assistant</h3>
              <p className="text-sm text-rose-600 mb-3">
                Show me flowers or spaces to get personalized recommendations
              </p>

              <div className="flex flex-col items-center justify-center w-full">
                <div className="relative w-full">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    className="w-full rounded-lg bg-black"
                  />
                  <div className="absolute bottom-2 right-2 bg-rose-900/75 text-white text-xs px-2 py-1 rounded-full">
                    {isCameraOn ? 'Camera active' : 'Camera inactive'}
                  </div>
                </div>

                <button
                  onClick={toggleCamera}
                  className="mt-2 flex items-center gap-2 px-3 py-1 rounded text-sm text-white transition-colors duration-200 ease-in-out bg-rose-500 hover:bg-rose-600"
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
                <p className="text-sm font-medium mb-2 text-rose-700">Last Captured Image:</p>
                <canvas
                  ref={canvasRef}
                  className="max-h-48 rounded-lg mx-auto object-contain border border-rose-200"
                />
              </div>
            </div>
          </div>

          <div 
            ref={transcriptContainerRef}
            className="mt-6 h-96 overflow-y-auto border border-rose-200 rounded-lg p-4 space-y-3"
          >
            {transcripts.length === 0 ? (
              <div className="text-rose-500 text-center">
                Start speaking to get floral recommendations and assistance
              </div>
            ) : (
              transcripts.map((transcript, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg border ${
                    transcript.type === 'user' 
                      ? 'bg-rose-50 border-rose-200'
                      : transcript.type === 'tool'
                      ? getToolStatusColor(transcript.toolStatus)
                      : 'bg-purple-50 border-purple-200'
                  }`}
                >
                  {transcript.type === 'tool' && transcript.toolName && (
                    <div className="flex items-center gap-2 mb-1 text-sm font-medium text-gray-600">
                      {getToolIcon(transcript.toolName)}
                      {transcript.toolName.replace(/_/g, ' ')}
                    </div>
                  )}
                  <div className="flex items-start gap-2">
                    <span className="font-semibold min-w-[3rem]">
                      {transcript.type === 'user' ? 'You' : 
                       transcript.type === 'tool' ? '' : 'Flora'}:
                    </span>
                    <span className="flex-1">{transcript.text}</span>
                  </div>
                  {transcript.metadata && (
                    <div className="text-xs text-gray-500 mt-1 pl-[3rem]">
                      Voice Clarity: {Math.round((1 + transcript.metadata.avg_logprob) * 100)}%
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </main>

        <footer className="mt-8 text-center text-rose-500 text-sm">
          <p>© 2025 - Flora's Flower Shop AI Assistant</p>
        </footer>
      </div>
      <Modal />
    </div>
  );
}

export default App;