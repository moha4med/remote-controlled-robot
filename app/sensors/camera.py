from picamera2 import Picamera2
import time
import threading

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        self.lock = threading.Lock()

        config = self.picam2.create_still_configuration(
            main={"size": (1280, 720), "format": "RGB888"}
        )

        self.picam2.configure(config)
        self.picam2.start()

        time.sleep(2)

    def capture_image(self, path="image.jpg"):
        self.picam2.capture_file(path)
        return path

    def get_frame(self):
        with self.lock:
            frame = self.picam2.capture_array()
        return frame
