# app/sensors/camera.py

import os
from datetime import datetime
from picamera2 import Picamera2
import cv2
import time
import threading

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

class Camera:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Camera, cls).__new__(cls)
            cls._instance.init_camera()
        return cls._instance
    
    def init_camera(self):
        self.picam2 = Picamera2()
        self.lock = threading.Lock()

        config = self.picam2.create_video_configuration(
            main={"size": (1280, 720), "format": "RGB888"}
        )

        self.picam2.configure(config)
        self.picam2.start()

        time.sleep(1)

    def get_frame(self):
        frame = self.picam2.capture_array()
        return frame
    
    def capture_image(self):
        frame = self.get_frame()

        save_dir = os.path.join(BASE_DIR, "app", "static", "captures")
        os.makedirs(save_dir, exist_ok=True)

        filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        full_path = os.path.join(save_dir, filename)

        cv2.imwrite(full_path, frame)

        return full_path

camera = Camera()
