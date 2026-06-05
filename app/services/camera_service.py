# app/services/camera_service.py

import cv2
import time
from app.sensors.camera import camera

def generate_stream():
    while True:
        frame = camera.get_frame()

        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.05)
        