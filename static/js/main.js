
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
            
            // Store the image in history
            if (window.ImageProcessor) {
                window.ImageProcessor.storeImage(capturedImage);
            }
            
            // Make the canvas container visible
            document.getElementById('captured-frame-container').classList.remove('hidden');
            
            return capturedImage;
        }
        
        return null;
    },
    
    // Get the last captured frame
    getLastFrame: function() {
        return this.capturedFrame;
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
        
        // Update UI to show if we're using image context
        const imageContextBadge = document.getElementById('image-context-badge');
        if (imageContextBadge) {
            const hasImageContext = imageData || (ImageProcessor.getRecentImages().length > 0);
            imageContextBadge.classList.toggle('hidden', !hasImageContext);
        }
        
        // If camera is active, get the captured frame
        if (CameraManager.isActive) {
            imageData = CameraManager.getLastFrame();
        }
        
        // Add current image if available
        if (imageData) {
            formData.append('has_image', 'true');
            formData.append('image_data', imageData);
        }
        
        // Add recent images history
        const recentImages = ImageProcessor.getRecentImages();
        if (recentImages && recentImages.length > 0) {
            formData.append('has_image_history', 'true');
            formData.append('image_history', JSON.stringify(recentImages));
        }
        
        // Add conversation history if available
        if (conversationHistory && conversationHistory.length > 0) {
            formData.append('conversation_history', JSON.stringify(conversationHistory));
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
    // Maximum number of recent images to track
    maxRecentImages: 3,
    
    // Convert image file to base64
    fileToBase64: function(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    },
    
    // Store image locally and manage image history
    storeImage: async function(imageFile, prefix = 'voice-assistant-image-') {
        try {
            let base64Image;
            
            // Handle both File objects and base64 strings
            if (typeof imageFile === 'string') {
                base64Image = imageFile;
            } else {
                base64Image = await this.fileToBase64(imageFile);
            }
            
            // Check size for localStorage (~5MB limit)
            if (base64Image.length > 5000000) {
                console.log("Resizing image to fit in localStorage");
                // Future enhancement: implement image resizing
            }
            
            // Store with timestamp key
            const imageKey = prefix + Date.now();
            localStorage.setItem(imageKey, base64Image);
            
            // Update current image key
            localStorage.setItem('current-image-key', imageKey);
            
            // Maintain a list of recent image keys (max 3)
            let recentImageKeys = JSON.parse(localStorage.getItem('recent-image-keys') || '[]');
            recentImageKeys.unshift(imageKey); // Add newest to the beginning
            
            // Keep only the most recent ones
            if (recentImageKeys.length > this.maxRecentImages) {
                // Get keys to remove
                const keysToRemove = recentImageKeys.splice(this.maxRecentImages);
                
                // Remove old images from storage
                keysToRemove.forEach(key => {
                    localStorage.removeItem(key);
                });
            }
            
            // Update the recent keys in storage
            localStorage.setItem('recent-image-keys', JSON.stringify(recentImageKeys));
            
            // Update UI to reflect image history
            this.updateImageHistoryUI();
            
            return {
                success: true,
                key: imageKey,
                data: base64Image
            };
        } catch (error) {
            console.error('Error storing image:', error);
            return {
                success: false,
                error: error.message
            };
        }
    },
    
    // Get all recent images
    getRecentImages: function() {
        const recentKeys = JSON.parse(localStorage.getItem('recent-image-keys') || '[]');
        return recentKeys.map(key => {
            return {
                key: key,
                data: localStorage.getItem(key)
            };
        }).filter(img => img.data !== null); // Filter out any null images
    },
    
    // Update the UI to display image history
    updateImageHistoryUI: function() {
        const imageHistoryContainer = document.getElementById('image-history');
        const imageHistoryCount = document.getElementById('image-history-count');
        
        if (!imageHistoryContainer) {
            console.error("Image history container not found in DOM");
            return;
        }
        
        // Get recent images
        const recentImages = this.getRecentImages();
        console.log(`Updating UI with ${recentImages.length} recent images`);
        
        // Update count
        if (imageHistoryCount) {
            imageHistoryCount.textContent = recentImages.length;
        }
        
        // Clear current history display
        imageHistoryContainer.innerHTML = '';
        
        // If no images, show placeholders
        if (!recentImages || recentImages.length === 0) {
            for (let i = 0; i < this.maxRecentImages; i++) {
                const placeholder = document.createElement('div');
                placeholder.className = 'image-placeholder w-24 h-24 bg-gray-100 rounded-lg border border-gray-300 flex items-center justify-center';
                placeholder.innerHTML = '<span class="text-gray-400 text-xs">Empty</span>';
                imageHistoryContainer.appendChild(placeholder);
            }
            return;
        }
        
        // Add recent images (newest first)
        recentImages.forEach((img, index) => {
            if (!img || img.length < 10) {
                console.error(`Invalid image data at index ${index}`);
                return;
            }
            
            const imgContainer = document.createElement('div');
            imgContainer.className = 'relative w-24 h-24 border border-gray-300 rounded-lg overflow-hidden';
            
            const imgElement = document.createElement('img');
            imgElement.src = img; // Use the img directly as it's the base64 data
            imgElement.className = 'w-full h-full object-cover';
            imgElement.alt = `Previous image ${index + 1}`;
            
            // Add index badge
            const indexBadge = document.createElement('div');
            indexBadge.className = 'absolute top-1 right-1 bg-blue-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center';
            indexBadge.textContent = index + 1;
            
            imgContainer.appendChild(imgElement);
            imgContainer.appendChild(indexBadge);
            imageHistoryContainer.appendChild(imgContainer);
        });
        
        // Add empty placeholders if less than max
        for (let i = recentImages.length; i < this.maxRecentImages; i++) {
            const placeholder = document.createElement('div');
            placeholder.className = 'image-placeholder w-24 h-24 bg-gray-100 rounded-lg border border-gray-300 flex items-center justify-center';
            placeholder.innerHTML = '<span class="text-gray-400 text-xs">Empty</span>';
            imageHistoryContainer.appendChild(placeholder);
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

// Initialize UI elements on load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize image history UI
    ImageProcessor.updateImageHistoryUI();
});

// Log to confirm the script loaded
console.log("Audio and Image Processing utilities loaded");
