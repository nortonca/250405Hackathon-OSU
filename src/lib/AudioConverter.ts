export class AudioConverter {
  static float32ToWav(audioData: Float32Array): Blob {
    const numChannels = 1;
    const sampleRate = 16000; // Required by Groq API
    const bitsPerSample = 16;

    const int16Array = new Int16Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
      const s = Math.max(-1, Math.min(1, audioData[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    const buffer = new ArrayBuffer(44 + int16Array.length * 2);
    const view = new DataView(buffer);

    const writeString = (view: DataView, offset: number, string: string) => {
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

    const offset = 44;
    for (let i = 0; i < int16Array.length; i++) {
      view.setInt16(offset + i * 2, int16Array[i], true);
    }

    return new Blob([buffer], { type: 'audio/wav' });
  }

  static async chunkAudio(audioData: Float32Array, chunkDurationMs: number = 30000): Promise<Blob[]> {
    const samplesPerChunk = Math.floor((chunkDurationMs / 1000) * 16000); // 16kHz sample rate
    const chunks: Blob[] = [];
    
    for (let i = 0; i < audioData.length; i += samplesPerChunk) {
      const chunkEnd = Math.min(i + samplesPerChunk, audioData.length);
      const chunk = audioData.slice(i, chunkEnd);
      chunks.push(this.float32ToWav(chunk));
    }

    return chunks;
  }
}