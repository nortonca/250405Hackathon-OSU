export class AudioPlayer {
  private static audioContext: AudioContext | null = null;
  private static audioElement: HTMLAudioElement | null = null;
  private static initialized = false;

  static init() {
    this.audioElement = document.createElement('audio');
    this.audioElement.style.display = 'none';
    document.body.appendChild(this.audioElement);

    this.audioElement.addEventListener('error', (e) => {
      console.error('Audio error:', e);
    });

    this.audioElement.addEventListener('playing', () => {
      console.log('Audio started playing');
    });

    this.audioElement.addEventListener('ended', () => {
      console.log('Audio playback completed');
    });

    document.addEventListener('click', () => {
      if (!this.audioContext) {
        try {
          this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
          console.log("Audio context initialized on user interaction");
          this.unlockAudio();
          this.initialized = true;
        } catch (error) {
          console.error("Could not unlock audio context:", error);
        }
      }
    }, { once: true });
  }

  private static unlockAudio() {
    if (!this.audioContext) return;

    const buffer = this.audioContext.createBuffer(1, 1, 22050);
    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext.destination);
    source.start(0);

    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
  }

  static playAudio(base64Audio: string) {
    if (!base64Audio || !this.audioElement) {
      console.error("No audio data or element available");
      return;
    }

    try {
      const audioSrc = `data:audio/mp3;base64,${base64Audio}`;
      this.audioElement.src = audioSrc;

      if (!this.initialized) {
        this.unlockAudio();
      }

      const playPromise = this.audioElement.play();

      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            console.log("Audio playback started successfully");
          })
          .catch(error => {
            console.error("Error playing audio:", error);
          });
      }
    } catch (error) {
      console.error("Error in playAudio:", error);
    }
  }
}