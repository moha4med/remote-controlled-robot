# app/routes/api/v1/ai.py
# API routes for AI-powered features, including environmental analysis and object detection

from flask import Blueprint, jsonify
from app.ai.services.environment_service import get_environment_analysis
from app.ai.detection.detector import detector
from app.models.capture import Capture

ai_bp = Blueprint("ai", __name__, url_prefix="/api/v1/ai")


@ai_bp.route("/environment", methods=["GET"])
def environment():
    analysis = get_environment_analysis()
    return jsonify(analysis)


@ai_bp.route("/detection/latest", methods=["GET"])
def detect_latest():
    capture = (
        Capture.query
        .order_by(Capture.created_at.desc())
        .first()
    )
    
    if not capture:
        return jsonify({"error": "No captures found"}), 404
    
    detections = detector.detect(capture.filepath)
    
    return jsonify({
        "capture": {
            "capture_id": capture.id,
            "filename": capture.filename,
            "filepath": capture.filepath,
            "created_at": capture.created_at.isoformat()
        },
        "detections": detections
    })
    

@ai_bp.route("/detection/image", methods=["GET"])
def detect_image():
    return jsonify({"message": "Not implemented yet"})