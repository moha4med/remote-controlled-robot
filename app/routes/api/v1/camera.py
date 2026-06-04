# app/routes/video.py

from flask import Blueprint, Response, render_template, send_file
from app.services.camera_service import generate_stream
from app.sensors.camera import camera

camera_bp = Blueprint(
    "camera",
    __name__,
    url_prefix="/api/v1/camera"
)

@camera_bp.route("/")
def index():
    return render_template('control.html')

@camera_bp.route("/video_feed")
def video_feed():
    return Response(
        generate_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@camera_bp.route("/capture")
def capture():
    path = camera.capture_image()

    return send_file(
        path,
        mimetype="image/jpeg",
        as_attachment=True
    )
