import { MicVAD } from '@ricky0123/vad-web';
import { AudioConverter } from './AudioConverter';
import { VisualAIService } from './VisualAIService';
import { SpeechService } from './SpeechService';

interface TranscriptionMetadata {
  id: string;
  seek?: number;
  start?: number;
  end?: number;
  avg_logprob?: number;
  compression_ratio?: number;
  no_speech_prob?: number;
}

interface TranscriptionResult {
  transcript: string;
  metadata: TranscriptionMetadata;
  aiResponse?: string;
}

export class AudioProcessor {
  private static vadInstance: any = null;
  private static isRecording = false;

  static async initVAD(callbacks: {
    onSpeechStart: () => void;
    onSpeechEnd: (audio: Float32Array) => void;
    onError: (error: Error) => void;
  }) {
    try {
      this.vadInstance = await MicVAD.new({
        onSpeechStart: () => {
          this.isRecording = true;
          callbacks.onSpeechStart();
        },
        onSpeechEnd: async (audio: Float32Array) => {
          this.isRecording = false;
          callbacks.onSpeechEnd(audio);
        },
        onVADMisfire: () => {
          console.log("VAD misfire (not speech)");
        }
      });
      return true;
    } catch (error) {
      callbacks.onError(error as Error);
      return false;
    }
  }

  static startListening() {
    if (this.vadInstance) {
      this.vadInstance.start();
    }
  }

  static stopListening() {
    if (this.vadInstance) {
      this.vadInstance.destroy();
      this.vadInstance = null;
    }
  }

  static async processPipeline(audio: Float32Array, imageData: string | null = null): Promise<TranscriptionResult> {
    try {
      // Convert audio to WAV format
      const audioChunks = await AudioConverter.chunkAudio(audio);
      let fullTranscript = '';
      let combinedMetadata: TranscriptionMetadata = {
        id: Date.now().toString()
      };

      // Process each chunk
      for (let i = 0; i < audioChunks.length; i++) {
        const formData = new FormData();
        formData.append('file', audioChunks[i], 'chunk.wav');
        formData.append('model', 'distil-whisper-large-v3-en');
        formData.append('response_format', 'verbose_json');
        formData.append('language', 'en');
        formData.append('temperature', '0');
        formData.append('timestamp_granularities[]', 'segment');

        const response = await fetch('https://api.groq.com/openai/v1/audio/transcriptions', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${import.meta.env.VITE_GROQ_API_KEY}`
          },
          body: formData
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Server error: ${response.status} - ${errorText}`);
        }

        const result = await response.json();

        // Append transcribed text
        fullTranscript += (i > 0 ? ' ' : '') + result.text;

        // Update metadata with quality indicators
        if (result.segments && result.segments.length > 0) {
          const lastSegment = result.segments[result.segments.length - 1];
          combinedMetadata = {
            ...combinedMetadata,
            avg_logprob: lastSegment.avg_logprob,
            compression_ratio: lastSegment.compression_ratio,
            no_speech_prob: lastSegment.no_speech_prob
          };
        }
      }

      // Get AI response with visual context
      const aiResponse = await VisualAIService.getResponse(fullTranscript.trim(), imageData);

      // Speak the AI response
      await SpeechService.speak(aiResponse);

      return {
        transcript: fullTranscript.trim(),
        metadata: combinedMetadata,
        aiResponse
      };
    } catch (error) {
      console.error('Error in audio processing:', error);
      throw error;
    }
  }
}