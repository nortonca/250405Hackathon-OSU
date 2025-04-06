import logging
import json
import time
import threading
import websocket
import base64
import queue
import os
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ServerConnection:
    """
    Manages the connection to the processing server for sending speech and image data.
    """
    
    def __init__(self, server_url=None, retry_limit=5, retry_delay=2.0, timeout=10.0):
        """
        Initialize server connection.
        
        Args:
            server_url (str): URL of the processing server, defaults to env variable
            retry_limit (int): Maximum number of retry attempts
            retry_delay (float): Delay between retry attempts in seconds
            timeout (float): Connection timeout in seconds
        """
        # Get server URL from environment or use default
        self.server_url = server_url or os.environ.get("SERVER_URL", "ws://localhost:8000/ws")
        self.retry_limit = retry_limit
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Connection state
        self.connected = False
        self.ws = None
        self.ws_lock = threading.Lock()
        
        # Message handling
        self.response_queue = queue.Queue()
        self.pending_requests = {}
        self.request_lock = threading.Lock()
        self.next_request_id = 1
        
        # Background thread for receiving messages
        self.receive_thread = None
        
        # Reconnection handling
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.last_reconnect_time = 0
        self.reconnect_backoff = 1.0  # Initial backoff in seconds
        
        logger.info(f"ServerConnection initialized with URL: {self.server_url}")
    
    def connect(self):
        """
        Connect to the server.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        with self.ws_lock:
            if self.connected and self.ws is not None:
                logger.info("Already connected to server")
                return True
                
            logger.info(f"Connecting to server at {self.server_url}")
            
            # Validate URL
            try:
                parsed_url = urlparse(self.server_url)
                if parsed_url.scheme not in ['ws', 'wss', 'http', 'https']:
                    logger.error(f"Invalid server URL scheme: {parsed_url.scheme}")
                    return False
            except Exception as e:
                logger.error(f"Invalid server URL: {str(e)}")
                return False
            
            # Determine if we're using WebSocket or HTTP
            is_websocket = parsed_url.scheme in ['ws', 'wss']
            
            try:
                if is_websocket:
                    # Connect using WebSocket
                    self.ws = websocket.WebSocketApp(
                        self.server_url,
                        on_open=self._on_open,
                        on_message=self._on_message,
                        on_error=self._on_error,
                        on_close=self._on_close
                    )
                    
                    # Start WebSocket in a thread
                    self.receive_thread = threading.Thread(target=self.ws.run_forever)
                    self.receive_thread.daemon = True
                    self.receive_thread.start()
                    
                    # Wait for connection to establish
                    connection_timeout = time.time() + self.timeout
                    while not self.connected and time.time() < connection_timeout:
                        time.sleep(0.1)
                    
                    if not self.connected:
                        logger.error("Connection timeout")
                        self._cleanup()
                        return False
                else:
                    # For HTTP, we'll just test the connection
                    http_url = f"http{'s' if parsed_url.scheme == 'https' else ''}://{parsed_url.netloc}/health"
                    response = requests.get(http_url, timeout=self.timeout)
                    if response.status_code == 200:
                        self.connected = True
                        logger.info("Connected to HTTP server successfully")
                    else:
                        logger.error(f"Failed to connect to HTTP server: {response.status_code}")
                        return False
                
                # Reset reconnection state on successful connection
                self.reconnect_attempts = 0
                self.reconnect_backoff = 1.0
                
                return self.connected
                
            except Exception as e:
                logger.error(f"Error connecting to server: {str(e)}")
                self._cleanup()
                return False
    
    def disconnect(self):
        """Disconnect from the server."""
        with self.ws_lock:
            if not self.connected:
                logger.info("Already disconnected from server")
                return
                
            logger.info("Disconnecting from server")
            
            # Close WebSocket if it exists
            if self.ws is not None:
                try:
                    self.ws.close()
                except Exception as e:
                    logger.error(f"Error closing WebSocket: {str(e)}")
            
            self._cleanup()
    
    def is_connected(self):
        """Check if connected to server."""
        return self.connected
    
    def send_speech_data(self, audio, image=None, image_analysis=None):
        """
        Send speech data to the server.
        
        Args:
            audio (bytes): Audio data
            image (bytes, optional): Image data captured during speech
            image_analysis (dict, optional): Results of image analysis
            
        Returns:
            dict: Response from server, or None if operation failed
        """
        if not self.connected:
            logger.warning("Not connected to server, attempting to connect")
            if not self.connect():
                logger.error("Failed to connect to server, speech data not sent")
                return None
        
        try:
            # Prepare request data
            with self.request_lock:
                request_id = self._get_next_request_id()
            
            request_data = {
                "request_id": request_id,
                "type": "speech_data",
                "timestamp": time.time()
            }
            
            # Add audio data
            if audio:
                if isinstance(audio, bytearray):
                    audio = bytes(audio)
                request_data["audio"] = base64.b64encode(audio).decode('utf-8')
            
            # Add image data if provided
            if image:
                request_data["image"] = base64.b64encode(image).decode('utf-8')
            
            # Add image analysis if provided
            if image_analysis:
                request_data["image_analysis"] = image_analysis
            
            # Send request
            success = self._send_request(request_data)
            if not success:
                logger.error("Failed to send speech data request")
                return None
            
            # Wait for response with timeout
            try:
                # Track the pending request
                with self.request_lock:
                    self.pending_requests[request_id] = None
                
                # Wait for response with timeout
                response_timeout = time.time() + self.timeout
                while time.time() < response_timeout:
                    with self.request_lock:
                        response = self.pending_requests.get(request_id)
                        if response is not None:
                            # Remove from pending requests
                            del self.pending_requests[request_id]
                            logger.debug(f"Received response for request {request_id}")
                            return response
                    
                    # Small sleep to prevent high CPU usage
                    time.sleep(0.1)
                
                # Timeout reached
                logger.warning(f"Response timeout for request {request_id}")
                with self.request_lock:
                    if request_id in self.pending_requests:
                        del self.pending_requests[request_id]
                
                return None
                
            except Exception as e:
                logger.error(f"Error waiting for response: {str(e)}")
                return None
            
        except Exception as e:
            logger.error(f"Error sending speech data: {str(e)}")
            return None
    
    def _send_request(self, request_data):
        """
        Send a request to the server.
        
        Args:
            request_data (dict): Request data to send
            
        Returns:
            bool: True if request was sent successfully, False otherwise
        """
        with self.ws_lock:
            if not self.connected or self.ws is None:
                logger.warning("Not connected to server")
                return False
            
            try:
                # Convert request data to JSON
                request_json = json.dumps(request_data)
                
                # Check if we're using WebSocket or HTTP
                parsed_url = urlparse(self.server_url)
                is_websocket = parsed_url.scheme in ['ws', 'wss']
                
                if is_websocket:
                    # Send via WebSocket
                    self.ws.send(request_json)
                else:
                    # Send via HTTP POST
                    http_url = f"http{'s' if parsed_url.scheme == 'https' else ''}://{parsed_url.netloc}/api/process"
                    response = requests.post(
                        http_url,
                        json=request_data,
                        headers={"Content-Type": "application/json"},
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        # For HTTP, we handle the response immediately
                        try:
                            response_data = response.json()
                            with self.request_lock:
                                self.pending_requests[request_data["request_id"]] = response_data
                        except Exception as e:
                            logger.error(f"Error parsing HTTP response: {str(e)}")
                            return False
                    else:
                        logger.error(f"HTTP request failed with status code: {response.status_code}")
                        return False
                
                logger.debug(f"Request sent successfully (id: {request_data.get('request_id')})")
                return True
                
            except Exception as e:
                logger.error(f"Error sending request: {str(e)}")
                # Mark as disconnected on error
                self._handle_connection_error()
                return False
    
    def _on_open(self, ws):
        """Called when WebSocket connection is established."""
        logger.info("WebSocket connection established")
        self.connected = True
    
    def _on_message(self, ws, message):
        """
        Called when a message is received from the server.
        
        Args:
            ws: WebSocket instance
            message (str): Message received
        """
        try:
            # Parse JSON message
            response = json.loads(message)
            
            # Check if it's a response to a request
            request_id = response.get("request_id")
            if request_id:
                with self.request_lock:
                    if request_id in self.pending_requests:
                        self.pending_requests[request_id] = response
                        logger.debug(f"Response received for request {request_id}")
                    else:
                        logger.warning(f"Received response for unknown request ID: {request_id}")
            else:
                logger.warning("Received message without request ID")
                
        except json.JSONDecodeError:
            logger.error("Received invalid JSON message")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    def _on_error(self, ws, error):
        """
        Called when a WebSocket error occurs.
        
        Args:
            ws: WebSocket instance
            error: Error that occurred
        """
        logger.error(f"WebSocket error: {str(error)}")
        self._handle_connection_error()
    
    def _on_close(self, ws, close_status_code, close_msg):
        """
        Called when WebSocket connection is closed.
        
        Args:
            ws: WebSocket instance
            close_status_code: Status code for close
            close_msg: Close message
        """
        logger.info(f"WebSocket connection closed (status: {close_status_code}, message: {close_msg})")
        self._handle_connection_error()
    
    def _handle_connection_error(self):
        """Handle connection error or disconnection."""
        was_connected = self.connected
        self.connected = False
        
        # Only attempt reconnect if we were previously connected
        if was_connected:
            self._maybe_reconnect()
    
    def _maybe_reconnect(self):
        """Attempt to reconnect to the server with backoff."""
        # Check if we've exceeded max reconnect attempts
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            return
        
        # Calculate backoff delay
        current_time = time.time()
        time_since_last_attempt = current_time - self.last_reconnect_time
        
        # Don't reconnect too frequently
        if time_since_last_attempt < self.reconnect_backoff:
            return
        
        # Update reconnection state
        self.reconnect_attempts += 1
        self.last_reconnect_time = current_time
        
        # Try to reconnect
        logger.info(f"Attempting to reconnect (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
        success = self.connect()
        
        if success:
            logger.info("Reconnection successful")
            self.reconnect_attempts = 0
            self.reconnect_backoff = 1.0
        else:
            # Increase backoff for next attempt (exponential backoff with max of 60 seconds)
            self.reconnect_backoff = min(self.reconnect_backoff * 2, 60.0)
            logger.warning(f"Reconnection failed, next attempt in {self.reconnect_backoff:.1f} seconds")
    
    def _cleanup(self):
        """Clean up resources."""
        self.connected = False
        self.ws = None
        
        # Clear pending requests
        with self.request_lock:
            self.pending_requests.clear()
    
    def _get_next_request_id(self):
        """Get the next request ID."""
        with self.request_lock:
            request_id = self.next_request_id
            self.next_request_id += 1
            return request_id
