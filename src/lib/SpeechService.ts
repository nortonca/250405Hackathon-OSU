export class SpeechService {
  private static audioContext: AudioContext | null = null;
  private static audioElement: HTMLAudioElement | null = null;
  private static voiceId = 'JBFqnCBsd6RMkjVDRZzb'; // Default voice ID

  static init() {
    if (!this.audioElement) {
      this.audioElement = new Audio();
      this.audioElement.addEventListener('error', (e) => {
        console.error('Audio playback error:', e);
      });
    }

    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
  }

  static async speak(text: string): Promise<void> {
    try {
      if (!text) return;

      this.init();

      const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${this.voiceId}?output_format=mp3_44100_128`, {
        method: 'POST',
        headers: {
          'xi-api-key': import.meta.env.VITE_ELEVENLABS_API_KEY,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
          model_id: 'eleven_flash_v2_5',
        }),
      });

      if (!response.ok) {
        throw new Error(`Speech synthesis failed: ${response.status}`);
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      if (this.audioElement) {
        this.audioElement.src = audioUrl;
        await this.audioElement.play();

        // Clean up the URL after playback
        this.audioElement.onended = () => {
          URL.revokeObjectURL(audioUrl);
        };
      }
    } catch (error) {
      console.error('Error in speech synthesis:', error);
      throw error;
    }
  }

  static stop() {
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement.currentTime = 0;
    }
  }
}