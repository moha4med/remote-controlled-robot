# app/services/stream_service.py

import cv2
from app.sensors.camera import camera

def generate_stream():
    while True:
        frame = camera.get_frame()

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
