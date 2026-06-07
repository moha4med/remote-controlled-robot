# app/routes/camera.py
# Camera streaming and capture endpoints

from flask import Blueprint, Response, render_template, send_file
from app.extensions import limiter
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
@limiter.limit("30/minute")
# @jwt_required_role("operator")  # uncomment to enable auth
def video_feed():
    """MJPEG video stream."""
    return Response(
        generate_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@camera_bp.route("/capture")
@limiter.limit("10/minute")
# @jwt_required_role("operator")  # uncomment to enable auth
def capture():
    """Capture a still image."""
    result = camera.capture_image()

    return send_file(
        result["filepath"],
        mimetype="image/jpeg",
        as_attachment=True
    )