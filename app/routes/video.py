from flask import Blueprint, render_template, Response
from app.sensors.camera import generate_frames

video_bp = Blueprint('video', __name__)

@video_bp.route('/')
def index():
    return render_template('index.html')

@video_bp.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
