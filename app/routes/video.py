from flask import Blueprint, Response, send_file
from app.services.stream_service import generate_stream
from app.sensors.camera import Camera

video_bp = Blueprint('video', __name__)

camera = Camera()

@video_bp.route('/video_feed')
def video_feed():
    return Response(
        generate_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@video_bp.route('/capture')
def capture():
    path = camera.capture_image("capture.jpg")
    return send_file(path, mimetype="image/type")
