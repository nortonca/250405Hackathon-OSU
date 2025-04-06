import logging
import os
import time
import json
import base64
import numpy as np
import threading
import uuid

logger = logging.getLogger(__name__)

def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Setup logging configuration.
    
    Args:
        log_level (int): Logging level (default: INFO)
        log_file (str, optional): File to write logs to
    """
    handlers = [logging.StreamHandler()]
    
    if log_file:
        try:
            handlers.append(logging.FileHandler(log_file))
        except Exception as e:
            print(f"Warning: Could not create log file: {str(e)}")
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    logger.info(f"Logging configured with level={logging.getLevelName(log_level)}")

def generate_id():
    """Generate a unique ID."""
    return str(uuid.uuid4())

def get_timestamp():
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)

def image_to_base64(image_data):
    """
    Convert image data to base64 string.
    
    Args:
        image_data (bytes): Image binary data
        
    Returns:
        str: Base64 encoded image string
    """
    if not image_data:
        return None
    
    try:
        return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Error converting image to base64: {str(e)}")
        return None

def base64_to_image(base64_str):
    """
    Convert base64 string to image data.
    
    Args:
        base64_str (str): Base64 encoded image string
        
    Returns:
        bytes: Image binary data
    """
    if not base64_str:
        return None
    
    try:
        return base64.b64decode(base64_str)
    except Exception as e:
        logger.error(f"Error converting base64 to image: {str(e)}")
        return None

def calculate_rms(audio_data, sample_width=2):
    """
    Calculate root mean square (RMS) of audio data.
    
    Args:
        audio_data (bytes): Audio data
        sample_width (int): Sample width in bytes
        
    Returns:
        float: RMS value between 0.0 and 1.0
    """
    if not audio_data:
        return 0.0
    
    try:
        # Convert bytes to numpy array
        if sample_width == 2:
            # 16-bit audio
            fmt = np.int16
            max_value = 32768.0
        elif sample_width == 1:
            # 8-bit audio
            fmt = np.uint8
            max_value = 256.0
        elif sample_width == 4:
            # 32-bit audio
            fmt = np.int32
            max_value = 2147483648.0
        else:
            logger.error(f"Unsupported sample width: {sample_width}")
            return 0.0
        
        # Convert to numpy array
        samples = np.frombuffer(audio_data, dtype=fmt)
        
        # Calculate RMS
        rms = np.sqrt(np.mean(np.square(samples.astype(np.float32)))) / max_value
        
        return float(rms)
    except Exception as e:
        logger.error(f"Error calculating RMS: {str(e)}")
        return 0.0

def safe_request(func, *args, retries=3, delay=1.0, **kwargs):
    """
    Execute a request function with retry logic.
    
    Args:
        func: Function to execute
        retries (int): Number of retry attempts
        delay (float): Delay between retries in seconds
        *args, **kwargs: Arguments to pass to func
        
    Returns:
        The result of func, or None if all retries failed
    """
    last_error = None
    
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                logger.warning(f"Request failed (attempt {attempt+1}/{retries}): {str(e)}")
                time.sleep(delay)
            else:
                logger.error(f"Request failed after {retries} attempts: {str(e)}")
    
    return None

def load_env_config(config_file=None):
    """
    Load configuration from environment variables and optionally from a config file.
    
    Args:
        config_file (str, optional): JSON configuration file
        
    Returns:
        dict: Configuration dictionary
    """
    # Default configuration
    config = {
        "server_url": os.environ.get("SERVER_URL", "ws://localhost:8000/ws"),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
        "history_file": os.environ.get("HISTORY_FILE", "conversation_history.json"),
        "camera_id": int(os.environ.get("CAMERA_ID", "0")),
        "vad_threshold": float(os.environ.get("VAD_THRESHOLD", "0.3"))
    }
    
    # Load from config file if provided
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
            logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Error loading configuration file: {str(e)}")
    
    return config

class RateLimit:
    """
    Simple rate limiter using token bucket algorithm.
    """
    
    def __init__(self, rate=1.0, capacity=1.0):
        """
        Initialize rate limiter.
        
        Args:
            rate (float): Rate at which tokens are added (per second)
            capacity (float): Maximum token bucket capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_time = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens=1.0):
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens (float): Number of tokens to consume
            
        Returns:
            bool: True if tokens were consumed, False otherwise
        """
        with self.lock:
            now = time.time()
            time_passed = now - self.last_time
            self.last_time = now
            
            # Add tokens based on time passed
            self.tokens = min(self.capacity, self.tokens + time_passed * self.rate)
            
            # Check if we have enough tokens
            if tokens <= self.tokens:
                self.tokens -= tokens
                return True
            else:
                return False
