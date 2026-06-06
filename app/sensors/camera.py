# app/sensors/camera.py

import os
import time
import threading
from datetime import datetime
import cv2
import numpy as np

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

# Try to import PiCamera2 — gracefully degrade if not available
try:
    from picamera2 import Picamera2
    HAS_PICAMERA = True
except ImportError:
    HAS_PICAMERA = False


class Camera:
    """Singleton camera with adaptive frame rate and shared frame buffer.

    Resources are minimised by:
    - Using a single background thread to capture frames into a shared buffer.
    - Dynamically adjusting capture rate based on how many readers are active.
    - Downscaling to 480p with controllable quality.
    - Using lock-free frame swapping where possible.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Camera, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._frame = None
        self._frame_lock = threading.Lock()
        self._reader_count = 0
        self._running = False
        self._thread = None
        self._picam2 = None
        self._use_software_fallback = False

        # Configuration
        self.target_fps = 10          # Normal capture rate
        self.low_fps = 2              # Rate when no readers
        self.resolution = (640, 480)  # Capture resolution
        self.jpeg_quality = 75        # JPEG encode quality (0-100)

        # Start the capture loop
        self._init_hardware()
        self._start_capture_loop()

    def _init_hardware(self):
        """Initialise PiCamera2, fall back to a test pattern if absent."""
        if HAS_PICAMERA:
            try:
                self._picam2 = Picamera2()
                config = self._picam2.create_video_configuration(
                    main={"size": self.resolution, "format": "RGB888"}
                )
                self._picam2.configure(config)
                self._picam2.start()
                time.sleep(1)  # Allow sensor to stabilise
                return
            except Exception as e:
                print(f"[CAMERA] PiCamera2 init failed: {e}")
        self._use_software_fallback = True
        print("[CAMERA] Using software fallback (test pattern)")

    def _capture_hardware_frame(self):
        """Capture a real frame from PiCamera2."""
        return self._picam2.capture_array()

    def _capture_fallback_frame(self):
        """Generate a test pattern frame when no camera is available."""
        import random
        frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
        # Dark grey background
        frame.fill(30)
        # Draw crosshair
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        cv2.line(frame, (cx - 30, cy), (cx + 30, cy), (80, 80, 80), 1)
        cv2.line(frame, (cx, cy - 30), (cx, cy + 30), (80, 80, 80), 1)
        cv2.circle(frame, (cx, cy), 10, (60, 60, 60), 1)
        # Text
        cv2.putText(frame, "NO CAMERA SIGNAL", (cx - 90, cy + 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
        cv2.putText(frame, f"Fallback mode", (cx - 60, cy + 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)
        return frame

    def _capture_frame(self):
        """Capture a single frame from hardware or fallback."""
        if self._picam2 is not None and not self._use_software_fallback:
            try:
                return self._capture_hardware_frame()
            except Exception:
                self._use_software_fallback = True
        return self._capture_fallback_frame()

    def _capture_loop(self):
        """Background loop that captures frames at adaptive rate."""
        frame_count = 0
        last_log = time.time()

        while self._running:
            with self._frame_lock:
                frame = self._capture_frame()
                # JPEG-encode for consistent memory and faster response
                _, buffer = cv2.imencode(
                    ".jpg", frame,
                    [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                )
                self._frame = buffer.tobytes()

            frame_count += 1
            now = time.time()
            # Log FPS every 10s
            if now - last_log >= 10:
                actual_fps = frame_count / (now - last_log)
                print(f"[CAMERA] ~{actual_fps:.1f} fps | readers: {self._reader_count}")
                frame_count = 0
                last_log = now

            # Adaptive sleep: run at target_fps when readers present, low_fps otherwise
            fps = self.target_fps if self._reader_count > 0 else self.low_fps
            time.sleep(1.0 / max(fps, 1))

    def _start_capture_loop(self):
        """Start the background capture thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="camera-capture")
        self._thread.start()

    def get_frame(self):
        """Return the latest JPEG-encoded frame as bytes.

        Thread-safe. The caller must call `release()` when done to
        decrement the reader count and allow FPS to drop.
        """
        self._reader_count += 1
        with self._frame_lock:
            if self._frame is not None:
                return self._frame
        # No frame yet — return a fallback
        frame = self._capture_fallback_frame()
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        return buffer.tobytes()

    def release(self):
        """Decrement reader count. Call when a client disconnects."""
        self._reader_count = max(0, self._reader_count - 1)

    def capture_image(self, jpeg_quality=90):
        """Capture a high-quality still image, save to disk, and generate a thumbnail.

        Returns:
            dict with filename, filepath, thumbnail_path, width, height, file_size
        """
        frame = self._capture_frame()
        save_dir = os.path.join(BASE_DIR, "app", "static", "captures")
        thumb_dir = os.path.join(save_dir, "thumbs")
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(thumb_dir, exist_ok=True)

        h, w = frame.shape[:2]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"capture_{timestamp}.jpg"
        thumb_filename = f"thumb_{timestamp}.jpg"
        full_path = os.path.join(save_dir, filename)
        thumb_path = os.path.join(thumb_dir, thumb_filename)

        # Save full resolution
        cv2.imwrite(full_path, frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])

        # Generate thumbnail (320px wide, maintain aspect ratio)
        thumb_w = 320
        thumb_h = int(h * (thumb_w / w))
        thumb = cv2.resize(frame, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
        cv2.imwrite(thumb_path, thumb, [cv2.IMWRITE_JPEG_QUALITY, 65])

        return {
            "filename": filename,
            "filepath": full_path,
            "thumbnail_path": thumb_path,
            "width": w,
            "height": h,
            "file_size": os.path.getsize(full_path),
        }

    def cleanup(self):
        """Stop the capture loop and release hardware."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        if self._picam2 is not None:
            try:
                self._picam2.stop()
                self._picam2.close()
            except Exception:
                pass


camera = Camera()