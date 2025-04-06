import logging
import cv2
import numpy as np
import base64
import io
import threading
import time
import traceback

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    """
    Handles capturing and analyzing images from a camera feed.
    """
    
    def __init__(self, camera_id=0, image_width=640, image_height=480):
        """
        Initialize the image analyzer.
        
        Args:
            camera_id (int): ID of the camera to use
            image_width (int): Width of the captured image
            image_height (int): Height of the captured image
        """
        self.camera_id = camera_id
        self.image_width = image_width
        self.image_height = image_height
        
        # Camera variables
        self.camera = None
        self.camera_lock = threading.Lock()
        self.last_capture_time = 0
        self.capture_cooldown = 1.0  # Minimum time between captures in seconds
        
        # Analysis settings
        self.face_cascade = None
        self.object_classes = None
        
        # Initialize required models
        self._initialize_models()
        
        logger.info(f"ImageAnalyzer initialized with camera_id={camera_id}, "
                   f"resolution={image_width}x{image_height}")
    
    def _initialize_models(self):
        """Initialize computer vision models."""
        try:
            # Load face detection model
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
            
            # For object detection we would normally use a more advanced model
            # like YOLO or SSD, but for simplicity, we're just using a basic
            # set of object classes that we can detect with color thresholding
            self.object_classes = ["person", "face", "text"]
            
            logger.info("Image analysis models loaded successfully")
        except Exception as e:
            logger.error(f"Failed to initialize image analysis models: {str(e)}")
            self.face_cascade = None
    
    def _ensure_camera_initialized(self):
        """Ensure camera is initialized and ready."""
        with self.camera_lock:
            if self.camera is None:
                try:
                    self.camera = cv2.VideoCapture(self.camera_id)
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.image_width)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.image_height)
                    
                    # Check if camera opened successfully
                    if not self.camera.isOpened():
                        logger.error("Failed to open camera")
                        self.camera = None
                        return False
                    
                    # Read a test frame to ensure camera is working
                    ret, _ = self.camera.read()
                    if not ret:
                        logger.error("Failed to read frame from camera")
                        self.camera.release()
                        self.camera = None
                        return False
                    
                    logger.info("Camera initialized successfully")
                    return True
                except Exception as e:
                    logger.error(f"Error initializing camera: {str(e)}")
                    if self.camera is not None:
                        self.camera.release()
                        self.camera = None
                    return False
            return self.camera.isOpened()
    
    def capture_image(self):
        """
        Capture an image from the camera.
        
        Returns:
            bytes: JPEG encoded image data, or None if capture failed
        """
        # Check if we need to respect cooldown
        current_time = time.time()
        if current_time - self.last_capture_time < self.capture_cooldown:
            logger.debug("Capture skipped due to cooldown")
            return None
        
        # Initialize camera if needed
        if not self._ensure_camera_initialized():
            logger.error("Camera not available for image capture")
            return None
        
        # Capture image
        with self.camera_lock:
            try:
                # Read frame
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    logger.error("Failed to capture frame")
                    # Attempt to reinitialize camera next time
                    self.camera.release()
                    self.camera = None
                    return None
                
                # Convert to JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                image_data = buffer.tobytes()
                
                # Update last capture time
                self.last_capture_time = current_time
                
                logger.debug(f"Image captured successfully ({len(image_data)} bytes)")
                return image_data
                
            except Exception as e:
                logger.error(f"Error capturing image: {str(e)}")
                # Print full stack trace for debugging
                logger.error(traceback.format_exc())
                return None
    
    def analyze_image(self, image_data):
        """
        Analyze the given image data.
        
        Args:
            image_data (bytes): JPEG encoded image data
            
        Returns:
            dict: Analysis results including detected faces, objects, etc.
        """
        if image_data is None:
            logger.warning("No image data provided for analysis")
            return {}
        
        try:
            # Convert image data to numpy array
            image_array = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("Failed to decode image for analysis")
                return {}
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Initialize results dictionary
            results = {
                "timestamp": time.time(),
                "image_dimensions": {
                    "width": image.shape[1],
                    "height": image.shape[0]
                },
                "faces": [],
                "objects": [],
                "scene_attributes": {}
            }
            
            # Detect faces if model available
            if self.face_cascade is not None:
                faces = self.face_cascade.detectMultiScale(
                    gray, 
                    scaleFactor=1.1, 
                    minNeighbors=5,
                    minSize=(30, 30)
                )
                
                for (x, y, w, h) in faces:
                    face_info = {
                        "position": {
                            "x": int(x),
                            "y": int(y),
                            "width": int(w),
                            "height": int(h)
                        },
                        "confidence": 0.9  # Placeholder
                    }
                    results["faces"].append(face_info)
            
            # Basic scene analysis
            # Calculate brightness
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            brightness = np.mean(hsv[:,:,2])
            
            # Calculate color distribution
            color_dist = {
                "red": float(np.mean(image[:,:,2])) / 255,
                "green": float(np.mean(image[:,:,1])) / 255,
                "blue": float(np.mean(image[:,:,0])) / 255
            }
            
            # Detect edges for complexity estimation
            edges = cv2.Canny(gray, 100, 200)
            edge_density = float(np.count_nonzero(edges)) / (edges.shape[0] * edges.shape[1])
            
            # Add scene attributes
            results["scene_attributes"] = {
                "brightness": float(brightness) / 255,
                "color_distribution": color_dist,
                "complexity": edge_density
            }
            
            logger.debug(f"Image analysis complete: {len(results['faces'])} faces detected")
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            # Print full stack trace for debugging
            logger.error(traceback.format_exc())
            return {}
    
    def close(self):
        """Release camera resources."""
        with self.camera_lock:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
                logger.info("Camera resources released")
