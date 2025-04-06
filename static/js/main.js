
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
    processPipeline: async function(audioData, imageData = null) {
        // Convert audio to WAV
        const wavBlob = this.float32ToWav(audioData);
        
        // Create form data
        const formData = new FormData();
        formData.append('audio', wavBlob, 'speech.wav');
        
        // Add image if available
        if (imageData) {
            formData.append('has_image', 'true');
            formData.append('image_data', imageData);
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

// Export utilities for use in main application
window.AudioProcessor = AudioProcessor;
window.ImageProcessor = ImageProcessor;
