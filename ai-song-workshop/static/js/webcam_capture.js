/**
 * WebcamCapture - Handles webcam access, preview, and photo capture.
 * Used by the photo transformation feature.
 */
class WebcamCapture {
    constructor(videoElement, canvasElement) {
        this.video = videoElement;
        this.canvas = canvasElement;
        this.stream = null;
        this.imageData = null;
    }

    /** Check if running on HTTPS (required for getUserMedia). */
    isSecureContext() {
        return location.protocol === 'https:' || location.hostname === 'localhost';
    }

    /** Request camera access and start preview. */
    async start() {
        if (!this.isSecureContext()) {
            throw new Error('Camera vereist een beveiligde verbinding (HTTPS).');
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Je browser ondersteunt geen camera toegang.');
        }
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false
            });
            this.video.srcObject = this.stream;
            await this.video.play();
        } catch (err) {
            if (err.name === 'NotAllowedError') {
                throw new Error('Camera toegang geweigerd. Sta camera toe in je browser.');
            } else if (err.name === 'NotFoundError') {
                throw new Error('Geen camera gevonden op dit apparaat.');
            }
            throw new Error('Kan camera niet starten: ' + err.message);
        }
    }

    /** Capture current frame as base64 PNG. */
    capture() {
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        const ctx = this.canvas.getContext('2d');
        ctx.drawImage(this.video, 0, 0);
        this.imageData = this.canvas.toDataURL('image/png');
        return this.imageData;
    }

    /** Get the last captured image data. */
    getImageData() {
        return this.imageData;
    }

    /** Stop camera and release stream. */
    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.video) {
            this.video.srcObject = null;
        }
    }
}
