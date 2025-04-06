export class CameraManager {
  private static stream: MediaStream | null = null;
  private static videoElement: HTMLVideoElement | null = null;
  private static canvasElement: HTMLCanvasElement | null = null;

  static init(videoElement: HTMLVideoElement, canvasElement: HTMLCanvasElement) {
    this.videoElement = videoElement;
    this.canvasElement = canvasElement;
  }

  static async startCamera(): Promise<boolean> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        }
      });

      if (this.videoElement) {
        this.videoElement.srcObject = this.stream;
        return true;
      }
      return false;
    } catch (error) {
      console.error("Error accessing camera:", error);
      return false;
    }
  }

  static stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      if (this.videoElement) {
        this.videoElement.srcObject = null;
      }
      this.stream = null;
    }
  }

  static captureFrame(): string | null {
    if (!this.videoElement || !this.canvasElement || !this.stream) return null;

    const context = this.canvasElement.getContext('2d');
    if (!context) return null;

    this.canvasElement.width = this.videoElement.videoWidth;
    this.canvasElement.height = this.videoElement.videoHeight;
    context.drawImage(this.videoElement, 0, 0);

    return this.canvasElement.toDataURL('image/jpeg', 0.85);
  }

  static get isActive(): boolean {
    return this.stream !== null;
  }
}