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
        try {
            // Convert audio to WAV
            const wavBlob = this.float32ToWav(audioData);
            console.log("Audio converted to WAV format");

            // Create form data
            const formData = new FormData();
            formData.append('audio', wavBlob, 'speech.wav');

            // Always use camera frame if active
            if (CameraManager.isActive) {
                imageData = CameraManager.getLastFrame();
                console.log("Using active camera frame");
            }

            // Must have image data
            if (!imageData) {
                console.error("Missing image data");
                throw new Error("Image data required for processing");
            }
            
            // Add image data
            formData.append('has_image', 'true');
            formData.append('image_data', imageData);
            console.log(`Image data added to form, length: ${imageData.length}`);
            
            // Send conversation history for context
            if (conversationHistory && conversationHistory.length > 0) {
                formData.append('conversation_history', JSON.stringify(conversationHistory));
                console.log(`Added conversation history with ${conversationHistory.length} messages`);
            }

            // Send to server
            console.log("Sending audio to server...");
            const response = await fetch('/transcribe', {
                method: 'POST',
                body: formData
            });

            console.log(`Server response status: ${response.status}`);
            if (!response.ok) {
                console.error("Error sending audio:", await response.text());
                throw new Error(`Server error: ${response.status}`);
            }

            const responseData = await response.json();
            console.log("Audio sent successfully");
            return responseData;
        } catch (error) {
            console.error("Error in audio processing:", error);
            throw error;
        }
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

            // Store with timestamp key
            const imageKey = prefix + Date.now();
            localStorage.setItem(imageKey, base64Image);
            localStorage.setItem('current-image-key', imageKey);

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