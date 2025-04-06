import logging
import threading
import queue
import numpy as np
import pyaudio
import wave
import os
import time
from array import array
from collections import deque

logger = logging.getLogger(__name__)

class VoiceActivityDetector:
    """
    Voice Activity Detection (VAD) module that processes audio input
    and detects speech segments.
    """
    
    def __init__(self, threshold=0.3, frame_duration=30, speech_timeout=1.0, silence_timeout=1.5):
        """
        Initialize VAD with configurable parameters.
        
        Args:
            threshold (float): Energy threshold for speech detection (0.0-1.0)
            frame_duration (int): Duration of audio frames in milliseconds
            speech_timeout (float): Time in seconds to confirm speech detection
            silence_timeout (float): Time in seconds of silence to end speech detection
        """
        self.threshold = threshold
        self.frame_duration = frame_duration
        self.speech_timeout = speech_timeout
        self.silence_timeout = silence_timeout
        
        # Audio settings
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000  # 16kHz sampling rate
        self.chunk_size = int(self.rate * frame_duration / 1000)  # Convert ms to samples
        
        # State variables
        self.running = False
        self.recording_thread = None
        self.audio = None
        
        # Speech detection state
        self.is_speech = False
        self.speech_energy_threshold = None  # Will be calculated dynamically
        self.speech_start_time = None
        self.silence_start_time = None
        
        # Energy history for dynamic threshold calculation
        self.energy_history = deque(maxlen=30)  # Keep energy history of last 30 frames
        
        # For debugging and tuning
        self.debug_mode = False
        self.energy_levels = []
        
        logger.info("VAD initialized with threshold=%.2f, frame_duration=%dms, speech_timeout=%.2fs, silence_timeout=%.2fs",
                   threshold, frame_duration, speech_timeout, silence_timeout)
    
    def start(self):
        """Start the VAD processing."""
        if self.running:
            logger.warning("VAD is already running")
            return
            
        logger.info("Starting VAD...")
        self.running = True
        self.is_speech = False
        self.speech_start_time = None
        self.silence_start_time = None
        self.energy_history.clear()
        self.energy_levels = []
        
        # Initialize PyAudio
        try:
            self.audio = pyaudio.PyAudio()
            
            # Start recording thread
            self.recording_thread = threading.Thread(target=self._process_audio)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
            logger.info("VAD started successfully")
        except Exception as e:
            logger.error(f"Failed to start VAD: {str(e)}")
            self.running = False
            if self.audio:
                self.audio.terminate()
                self.audio = None
    
    def stop(self):
        """Stop the VAD processing."""
        if not self.running:
            logger.warning("VAD is already stopped")
            return
            
        logger.info("Stopping VAD...")
        self.running = False
        
        # Wait for recording thread to finish
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=2.0)
            
        # Cleanup PyAudio
        if self.audio:
            self.audio.terminate()
            self.audio = None
            
        logger.info("VAD stopped")
    
    def is_speech_detected(self):
        """Check if speech is currently detected."""
        return self.is_speech
    
    def _process_audio(self):
        """Process audio input to detect speech."""
        logger.info("Audio processing thread started")
        
        try:
            # Open audio stream
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            # Calibration phase - collect background noise samples
            logger.info("Calibrating VAD - collecting background noise samples...")
            self._calibrate(stream)
            
            logger.info("VAD calibration complete, speech_energy_threshold=%.4f", self.speech_energy_threshold)
            
            # Main processing loop
            while self.running:
                # Read audio chunk
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Process the audio chunk for speech detection
                self._process_chunk(data)
                
                # Small sleep to reduce CPU usage
                time.sleep(0.01)
            
            # Cleanup
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            logger.error(f"Error in audio processing: {str(e)}")
            self.running = False
    
    def _calibrate(self, stream):
        """Calibrate the VAD by analyzing background noise."""
        # Collect background noise for 2 seconds
        calibration_chunks = []
        for _ in range(int(2.0 * self.rate / self.chunk_size)):
            data = stream.read(self.chunk_size, exception_on_overflow=False)
            calibration_chunks.append(data)
            time.sleep(0.01)
        
        # Calculate average energy of background noise
        energies = [self._calculate_energy(chunk) for chunk in calibration_chunks]
        avg_energy = np.mean(energies) if energies else 0.05
        
        # Set threshold as a multiple of average background noise
        # Using 2.5x for a balance between sensitivity and false positives
        self.speech_energy_threshold = avg_energy * 2.5
        
        # Ensure minimum threshold
        self.speech_energy_threshold = max(self.speech_energy_threshold, 0.01)
        
        # Apply user threshold factor
        self.speech_energy_threshold *= self.threshold
        
        # Initialize energy history with calibration data
        self.energy_history.extend(energies)
    
    def _calculate_energy(self, data):
        """Calculate the energy level of an audio chunk."""
        # Convert bytes to array of short integers
        audio_array = array('h', data)
        
        # Calculate RMS energy
        if len(audio_array) == 0:
            return 0.0
            
        # Normalize to 0.0-1.0 range based on 16-bit audio
        max_value = 32767.0  # Max value for 16-bit audio
        energy = np.sqrt(np.mean(np.square([x / max_value for x in audio_array])))
        
        return energy
    
    def _process_chunk(self, data):
        """Process a single audio chunk for speech detection."""
        # Calculate energy of current chunk
        current_energy = self._calculate_energy(data)
        
        # Store energy for dynamic threshold calculation
        self.energy_history.append(current_energy)
        
        # Dynamic threshold adjustment
        if len(self.energy_history) >= 10:
            # Recalculate threshold periodically using recent history
            # This helps adapt to changing background noise conditions
            sorted_energies = sorted(self.energy_history)
            # Use the energy at the 30th percentile as the base
            base_energy = sorted_energies[int(len(sorted_energies) * 0.3)]
            # Apply multiplier and user threshold
            self.speech_energy_threshold = max(base_energy * 2.0 * self.threshold, 0.01)
        
        # For debugging
        if self.debug_mode:
            self.energy_levels.append((current_energy, self.speech_energy_threshold))
            if len(self.energy_levels) % 100 == 0:
                logger.debug(f"Energy: {current_energy:.4f}, Threshold: {self.speech_energy_threshold:.4f}")
        
        # Speech detection logic
        current_time = time.time()
        
        if current_energy > self.speech_energy_threshold:
            # Energy above threshold - potential speech
            if not self.is_speech:
                # First time detecting potential speech
                if self.speech_start_time is None:
                    self.speech_start_time = current_time
                    logger.debug("Potential speech detected, waiting for confirmation")
                
                # Check if speech has been detected long enough to confirm
                elif current_time - self.speech_start_time >= self.speech_timeout:
                    self.is_speech = True
                    logger.debug("Speech confirmed")
            
            # Reset silence timer if we're already in speech mode
            self.silence_start_time = None
            
        else:
            # Energy below threshold - potential silence
            if self.is_speech:
                # First time detecting potential silence
                if self.silence_start_time is None:
                    self.silence_start_time = current_time
                    logger.debug("Potential end of speech, waiting for confirmation")
                
                # Check if silence has been detected long enough to end speech
                elif current_time - self.silence_start_time >= self.silence_timeout:
                    self.is_speech = False
                    self.speech_start_time = None
                    logger.debug("End of speech confirmed")
            else:
                # Reset speech timer if we're in silence mode
                self.speech_start_time = None
