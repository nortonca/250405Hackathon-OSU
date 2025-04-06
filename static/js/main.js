
// Camera Management Utilities
const CameraManager = {
    videoElement: null,
    stream: null,
    capturedFrame: null,
    canvas: null,
    context: null,
    isActive: false,
    
    // Initialize camera manager
    init: function(videoElementId, canvasElementId) {
        this.videoElement = document.getElementById(videoElementId);
        this.canvas = document.getElementById(canvasElementId);
        this.context = this.canvas.getContext('2d');
        this.capturedFrame = null;
    },
    
    // Start camera stream
    startCamera: async function() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: "user"
                }, 
                audio: false 
            });
            
            this.videoElement.srcObject = this.stream;
            this.isActive = true;
            return true;
        } catch (error) {
            console.error("Error accessing camera:", error);
            return false;
        }
    },
    
    // Stop camera stream
    stopCamera: function() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.videoElement.srcObject = null;
            this.isActive = false;
        }
    },
    
    // Capture current frame
    captureFrame: function() {
        if (!this.isActive || !this.videoElement) return null;
        
        // Set canvas size to match video dimensions
        const width = this.videoElement.videoWidth;
        const height = this.videoElement.videoHeight;
        
        if (width && height) {
            this.canvas.width = width;
            this.canvas.height = height;
            this.context.drawImage(this.videoElement, 0, 0, width, height);
            
            // Get base64 representation of the image
            const capturedImage = this.canvas.toDataURL('image/jpeg');
            this.capturedFrame = capturedImage;
            
            // Make the canvas container visible
            document.getElementById('captured-frame-container').classList.remove('hidden');
            
            return capturedImage;
        }
        
        return null;
    },
    
    // Get the last captured frame
    getLastFrame: function() {
        return this.capturedFrame;
    },
    
    // Clear last captured frame
    clearCapturedFrame: function() {
        this.capturedFrame = null;
        const container = document.getElementById('captured-frame-container');
        if (container) {
            container.classList.add('hidden');
        }
        if (this.canvas) {
            this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    }
};

// Image History Management
const ImageHistoryManager = {
    // Maximum number of images to keep in history
    maxImages: 5,
    
    // Get stored image history
    getHistory: function() {
        const keys = this.getHistoryKeys();
        const history = [];
        
        for (const key of keys) {
            const imageData = localStorage.getItem(key);
            if (imageData) {
                history.push({
                    key: key,
                    data: imageData,
                    timestamp: parseInt(key.split('-').pop(), 10)
                });
            }
        }
        
        return history.sort((a, b) => a.timestamp - b.timestamp);
    },
    
    // Get image history keys from localStorage
    getHistoryKeys: function() {
        const keys = [];
        const prefix = 'voice-assistant-image-';
        
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(prefix)) {
                keys.push(key);
            }
        }
        
        return keys;
    },
    
    // Add image to history
    addToHistory: function(imageData) {
        // Create a new key with timestamp
        const imageKey = 'voice-assistant-image-' + Date.now();
        localStorage.setItem(imageKey, imageData);
        localStorage.setItem('current-image-key', imageKey);
        
        // Keep history size limited
        this.pruneHistory();
        
        return imageKey;
    },
    
    // Limit the number of stored images
    pruneHistory: function() {
        const keys = this.getHistoryKeys();
        if (keys.length > this.maxImages) {
            // Sort by timestamp (oldest first)
            keys.sort((a, b) => {
                const timeA = parseInt(a.split('-').pop(), 10);
                const timeB = parseInt(b.split('-').pop(), 10);
                return timeA - timeB;
            });
            
            // Remove oldest images
            const toRemove = keys.length - this.maxImages;
            for (let i = 0; i < toRemove; i++) {
                localStorage.removeItem(keys[i]);
            }
        }
    },
    
    // Clear all image history
    clearAllHistory: function() {
        // Remove current image key
        localStorage.removeItem('current-image-key');
        
        // Remove all history images
        const keys = this.getHistoryKeys();
        keys.forEach(key => {
            localStorage.removeItem(key);
        });
        
        // Update UI
        this.renderInUI('image-history-container');
    },
    
    // Render image history in UI
    renderInUI: function(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const history = this.getHistory();
        container.innerHTML = '';
        
        if (history.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-sm text-center">No image history</p>';
            return;
        }
        
        // Create history display
        history.forEach((item, index) => {
            const thumbnail = document.createElement('div');
            thumbnail.className = 'image-thumbnail';
            thumbnail.innerHTML = `
                <img src="${item.data}" class="w-full h-16 object-cover rounded-md" 
                     title="Image ${index + 1} from history">
                <span class="text-xs text-gray-500 text-center block mt-1">
                    Used for context
                </span>
            `;
            container.appendChild(thumbnail);
        });
    }
};

// Audio Processing Utilities
const AudioProcessor = {
    // Convert Float32Array to WAV format
    float32ToWav: function(audioData, sampleRate = 16000) {
        const numChannels = 1;
        const bitsPerSample = 16;
        
        // Convert Float32Array to Int16Array
        const int16Array = new Int16Array(audioData.length);
        for (let i = 0; i < audioData.length; i++) {
            const s = Math.max(-1, Math.min(1, audioData[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        
        // Create WAV file
        const buffer = new ArrayBuffer(44 + int16Array.length * 2);
        const view = new DataView(buffer);
        
        const writeString = (view, offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };
        
        // Write WAV header
        writeString(view, 0, 'RIFF');
        view.setUint32(4, 36 + int16Array.length * 2, true);
        writeString(view, 8, 'WAVE');
        
        writeString(view, 12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, numChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * numChannels * bitsPerSample / 8, true);
        view.setUint16(32, numChannels * bitsPerSample / 8, true);
        view.setUint16(34, bitsPerSample, true);
        
        writeString(view, 36, 'data');
        view.setUint32(40, int16Array.length * 2, true);
        
        // Write PCM samples
        const offset = 44;
        for (let i = 0; i < int16Array.length; i++) {
            view.setInt16(offset + i * 2, int16Array[i], true);
        }
        
        return new Blob([buffer], { type: 'audio/wav' });
    },
    
    // Process audio pipeline
    processPipeline: async function(audioData, imageData = null, conversationHistory = []) {
        // Convert audio to WAV
        const wavBlob = this.float32ToWav(audioData);
        
        // Create form data
        const formData = new FormData();
        formData.append('audio', wavBlob, 'speech.wav');
        
        // If camera is active, get the captured frame
        if (CameraManager.isActive) {
            imageData = CameraManager.getLastFrame();
        }
        
        // Add image if available
        let hasImage = false;
        if (imageData) {
            hasImage = true;
            formData.append('has_image', 'true');
            formData.append('image_data', imageData);
        }
        
        // Add conversation history if available
        if (conversationHistory && conversationHistory.length > 0) {
            // Ensure image data is properly included in the conversation history
            const processedHistory = conversationHistory.map(msg => {
                // Create a copy to avoid modifying the original
                const msgCopy = {...msg};
                
                // For user messages that had images, add the image flag and data
                if (msgCopy.role === 'user' && msgCopy.hasOwnProperty('image_data')) {
                    msgCopy.has_image = true;
                }
                
                return msgCopy;
            });
            
            formData.append('conversation_history', JSON.stringify(processedHistory));
        }
        
        // Send to server
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        return await response.json();
    }
};

// Image processing utilities
const ImageProcessor = {
    // Convert image file to base64
    fileToBase64: function(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    },
    
    // Store image locally
    storeImage: async function(imageFile, prefix = 'voice-assistant-image-') {
        try {
            const base64Image = await this.fileToBase64(imageFile);
            
            // Check size for localStorage (~5MB limit)
            if (base64Image.length > 5000000) {
                throw new Error('Image too large for local storage');
            }
            
            // Add to history using the history manager
            const imageKey = ImageHistoryManager.addToHistory(base64Image);
            
            // Update UI if the history container exists
            if (document.getElementById('image-history-container')) {
                ImageHistoryManager.renderInUI('image-history-container');
            }
            
            // Return information about the stored image
            return {
                success: true,
                key: imageKey,
                data: base64Image,
                historySize: ImageHistoryManager.getHistory().length
            };
        } catch (error) {
            console.error('Error storing image:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }
};

// Export utilities for use in main application - make sure they're globally available
window.AudioProcessor = AudioProcessor;
window.ImageProcessor = ImageProcessor;

// For compatibility with older browsers
if (typeof AudioProcessor === 'undefined') {
    console.log("Creating global AudioProcessor");
    globalThis.AudioProcessor = AudioProcessor;
}
if (typeof ImageProcessor === 'undefined') {
    console.log("Creating global ImageProcessor");
    globalThis.ImageProcessor = ImageProcessor;
}

// Log to confirm the script loaded
console.log("Audio and Image Processing utilities loaded");
