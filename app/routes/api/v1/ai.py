# app/routes/api/v1/ai.py
# API routes for AI-powered features, including environmental analysis and object detection

import cv2
import traceback
from flask import Blueprint, jsonify
from app.ai.services.environment_service import get_environment_analysis
from app.ai.detection.detector import ObjectDetector
from app.models.capture import Capture

ai_bp = Blueprint("ai", __name__, url_prefix="/api/v1/ai")

detector = ObjectDetector()


@ai_bp.route("/environment", methods=["GET"])
def environment():
    analysis = get_environment_analysis()
    return jsonify(analysis)


@ai_bp.route("/detection/latest", methods=["GET"])
def detect_latest():
    capture = Capture.query.order_by(Capture.created_at.desc()).first()

    if not capture:
        return jsonify({"error": "No captures found"}), 404

    frame = cv2.imread(capture.filepath)

    if frame is None:
        return jsonify({"error": f"Could not read image at {capture.filepath}"}), 500

    try:
        detections = detector.detect(frame)
    except MemoryError:
        return jsonify({
            "error": "Out of memory during inference. Try a smaller image or restart the service."
        }), 503
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Detection failed: {str(e)}"}), 500

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