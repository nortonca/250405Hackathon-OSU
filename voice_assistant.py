import logging
import time
import threading
import queue
import os
from vad import VoiceActivityDetector
from server_connection import ServerConnection
from image_analyzer import ImageAnalyzer
from conversation import ConversationManager
import utils

logger = logging.getLogger(__name__)

class VoiceAssistant:
    def __init__(self):
        """Initialize the voice assistant with all necessary components."""
        logger.info("Initializing Voice Assistant...")
        
        # Initialize components
        self.vad = VoiceActivityDetector(
            threshold=0.3,  # Lower threshold to improve detection
            frame_duration=30,  # Larger frame size for better accuracy
            speech_timeout=1.0,  # Longer timeout to avoid early cutoffs
            silence_timeout=1.5  # Longer silence to properly detect end of speech
        )
        
        self.server = ServerConnection(
            retry_limit=5,
            retry_delay=2.0,
            timeout=10.0
        )
        
        self.image_analyzer = ImageAnalyzer()
        self.conversation = ConversationManager()
        
        # Setup state variables
        self.running = False
        self.recent_events = []
        self.event_lock = threading.Lock()
        self.speech_queue = queue.Queue()
        self.processing_thread = None
        self.vad_state = "idle"
        
        # Track connection attempts
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        
        logger.info("Voice Assistant initialized successfully")
        
    def start(self):
        """Start the voice assistant."""
        if self.running:
            logger.warning("Voice assistant is already running")
            return
            
        logger.info("Starting voice assistant...")
        self.running = True
        
        # Connect to server
        if not self._connect_to_server():
            logger.error("Failed to connect to server, voice assistant not started")
            self.running = False
            return
        
        # Start VAD
        self.vad.start()
        
        # Start speech processing thread
        self.processing_thread = threading.Thread(target=self._process_speech_events)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Main loop to monitor VAD events
        try:
            while self.running:
                if self.vad.is_speech_detected():
                    if self.vad_state != "speaking":
                        logger.debug("Speech started")
                        self._add_event("Speech detected")
                        self.vad_state = "speaking"
                        
                        # Capture image when speech starts
                        image_data = self.image_analyzer.capture_image()
                        if image_data:
                            self.speech_queue.put({
                                "type": "speech_start",
                                "timestamp": time.time(),
                                "image": image_data
                            })
                else:
                    if self.vad_state == "speaking":
                        logger.debug("Speech ended")
                        self._add_event("Speech ended")
                        self.vad_state = "idle"
                        
                        # Signal end of speech event
                        self.speech_queue.put({
                            "type": "speech_end",
                            "timestamp": time.time()
                        })
                
                # Check server connection periodically
                if not self.server.is_connected() and self.running:
                    logger.warning("Server connection lost, attempting to reconnect")
                    self._connect_to_server()
                
                time.sleep(0.1)  # Sleep to prevent high CPU usage
                
        except Exception as e:
            logger.error(f"Error in voice assistant main loop: {str(e)}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the voice assistant and all components."""
        if not self.running:
            logger.warning("Voice assistant is already stopped")
            return
            
        logger.info("Stopping voice assistant...")
        self.running = False
        
        # Stop all components
        if self.vad:
            self.vad.stop()
        
        if self.server:
            self.server.disconnect()
        
        # Signal the processing thread to exit
        self.speech_queue.put(None)
        
        # Wait for processing thread to finish
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
            
        logger.info("Voice assistant stopped")
    
    def _process_speech_events(self):
        """Process speech events from the queue."""
        logger.info("Speech processing thread started")
        
        current_speech_data = None
        
        while self.running:
            try:
                # Get event from queue (with timeout to allow checking if running)
                event = self.speech_queue.get(timeout=1.0)
                
                # None is a signal to exit
                if event is None:
                    break
                
                event_type = event.get("type")
                
                if event_type == "speech_start":
                    # Start of new speech - initialize
                    current_speech_data = {
                        "start_time": event.get("timestamp"),
                        "image": event.get("image"),
                        "audio_buffer": bytearray(),
                        "transcription": None
                    }
                    
                    self._add_event("Processing speech start")
                    
                    # Analyze image if available
                    if current_speech_data.get("image"):
                        image_analysis = self.image_analyzer.analyze_image(current_speech_data["image"])
                        current_speech_data["image_analysis"] = image_analysis
                        self._add_event("Image analyzed")
                
                elif event_type == "speech_end" and current_speech_data:
                    # End of speech - finalize processing
                    current_speech_data["end_time"] = event.get("timestamp")
                    
                    # Only process if we have actual audio data
                    if len(current_speech_data.get("audio_buffer", b"")) > 0:
                        self._add_event("Processing full speech")
                        
                        # Send to server for processing
                        if self.server.is_connected():
                            response = self.server.send_speech_data(
                                audio=current_speech_data["audio_buffer"],
                                image=current_speech_data.get("image"),
                                image_analysis=current_speech_data.get("image_analysis", {})
                            )
                            
                            if response:
                                # Update conversation history
                                self.conversation.add_interaction(
                                    user_input=response.get("transcription", ""),
                                    system_response=response.get("response", ""),
                                    metadata={
                                        "has_image": current_speech_data.get("image") is not None,
                                        "duration": current_speech_data["end_time"] - current_speech_data["start_time"]
                                    }
                                )
                                self._add_event("Conversation updated")
                            else:
                                self._add_event("Server processing failed", error=True)
                        else:
                            self._add_event("Server not connected, speech not processed", error=True)
                    else:
                        self._add_event("Empty speech detected, ignoring", error=True)
                    
                    # Reset current speech data
                    current_speech_data = None
                
                elif event_type == "audio_chunk" and current_speech_data:
                    # Append audio chunk to current speech
                    audio_chunk = event.get("audio")
                    if audio_chunk:
                        current_speech_data["audio_buffer"].extend(audio_chunk)
                
                self.speech_queue.task_done()
                
            except queue.Empty:
                # This is normal due to the timeout - just continue
                continue
            except Exception as e:
                logger.error(f"Error processing speech event: {str(e)}")
                self._add_event(f"Processing error: {str(e)}", error=True)
        
        logger.info("Speech processing thread stopped")
    
    def _connect_to_server(self):
        """Connect to the server with retry logic."""
        if self.server.is_connected():
            return True
            
        self.connection_attempts += 1
        if self.connection_attempts > self.max_connection_attempts:
            logger.error(f"Maximum connection attempts ({self.max_connection_attempts}) reached")
            self._add_event("Max server connection attempts reached", error=True)
            return False
            
        logger.info(f"Connecting to server (attempt {self.connection_attempts})")
        self._add_event(f"Connecting to server (attempt {self.connection_attempts})")
        
        success = self.server.connect()
        if success:
            logger.info("Connected to server successfully")
            self._add_event("Server connected")
            # Reset connection attempts on success
            self.connection_attempts = 0
            return True
        else:
            logger.warning("Failed to connect to server")
            self._add_event("Server connection failed", error=True)
            return False
    
    def _add_event(self, message, error=False):
        """Add a new event to the recent events list."""
        with self.event_lock:
            event = {
                "timestamp": time.time(),
                "message": message,
                "is_error": error
            }
            self.recent_events.append(event)
            # Keep only the last 20 events
            if len(self.recent_events) > 20:
                self.recent_events.pop(0)
    
    def get_recent_events(self):
        """Get the list of recent events."""
        with self.event_lock:
            return self.recent_events.copy()
    
    def get_conversation_history(self):
        """Get the conversation history."""
        return self.conversation.get_history()
    
    def is_server_connected(self):
        """Check if server is connected."""
        return self.server.is_connected() if self.server else False
    
    def get_vad_state(self):
        """Get the current VAD state."""
        return self.vad_state
