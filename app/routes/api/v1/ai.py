# app/routes/api/v1/ai.py
# API routes for AI-powered features, including environmental analysis and object detection
# Enhanced with comprehensive debug logging for troubleshooting detection issues

import cv2
import time
import traceback
from flask import Blueprint, jsonify
from app.ai.services.environment_service import get_environment_analysis
from app.ai.detection.detector import ObjectDetector
from app.models.capture import Capture
from app.services.event_capture import check_detection_snapshot
from app.services.data_logger import data_logger

ai_bp = Blueprint("ai", __name__, url_prefix="/api/v1/ai")

detector = ObjectDetector()


@ai_bp.route("/environment", methods=["GET"])
def environment():
    analysis = get_environment_analysis()
    return jsonify(analysis)


@ai_bp.route("/detection/latest", methods=["GET"])
def detect_latest():
    t_start = time.time()
    data_logger.info("detection/latest: request received", component="detection_route")

    # Step 1: Fetch latest capture from DB
    t_db = time.time()
    try:
        capture = Capture.query.order_by(Capture.created_at.desc()).first()
        data_logger.debug(
            f"detection/latest: DB query took {(time.time()-t_db)*1000:.1f}ms",
            component="detection_route"
        )
    except Exception as e:
        data_logger.error(
            f"detection/latest: DB query failed: {e}",
            component="detection_route",
            details=traceback.format_exc()
        )
        return jsonify({"error": f"Database query failed: {str(e)}"}), 500

    if not capture:
        data_logger.warning(
            "detection/latest: no captures found in database",
            component="detection_route"
        )
        return jsonify({"error": "No captures found"}), 404

    data_logger.info(
        f"detection/latest: found capture id={capture.id}, filename='{capture.filename}', "
        f"filepath='{capture.filepath}', created_at={capture.created_at.isoformat()}",
        component="detection_route"
    )

    # Step 2: Validate filepath
    if not capture.filepath:
        data_logger.error(
            f"detection/latest: capture {capture.id} has empty filepath",
            component="detection_route"
        )
        return jsonify({"error": "Capture has no filepath"}), 500

    import os
    if not os.path.exists(capture.filepath):
        data_logger.error(
            f"detection/latest: file does not exist on disk: '{capture.filepath}'",
            component="detection_route"
        )
        return jsonify({
            "error": f"Image file not found on disk",
            "filepath": capture.filepath,
            "hint": "The file may have been deleted or the path is incorrect"
        }), 404

    file_size = os.path.getsize(capture.filepath)
    data_logger.debug(
        f"detection/latest: file exists, size={file_size} bytes",
        component="detection_route"
    )

    if file_size == 0:
        data_logger.error(
            f"detection/latest: file is empty (0 bytes): '{capture.filepath}'",
            component="detection_route"
        )
        return jsonify({"error": "Image file is empty (0 bytes)"}), 500

    # Step 3: Read image with OpenCV
    t_read = time.time()
    try:
        frame = cv2.imread(capture.filepath)
        read_ms = (time.time() - t_read) * 1000
        data_logger.debug(
            f"detection/latest: cv2.imread took {read_ms:.1f}ms",
            component="detection_route"
        )
    except Exception as e:
        data_logger.error(
            f"detection/latest: cv2.imread exception: {e}",
            component="detection_route",
            details=traceback.format_exc()
        )
        return jsonify({"error": f"Failed to read image: {str(e)}"}), 500

    if frame is None:
        data_logger.error(
            f"detection/latest: cv2.imread returned None for '{capture.filepath}'. "
            f"File may be corrupted or in unsupported format.",
            component="detection_route"
        )
        return jsonify({
            "error": f"Could not read image — file may be corrupted",
            "filepath": capture.filepath,
            "file_size": file_size
        }), 500

    data_logger.info(
        f"detection/latest: image loaded — shape={frame.shape}, dtype={frame.dtype}",
        component="detection_route"
    )

    # Step 4: Run object detection
    t_detect = time.time()
    try:
        detections = detector.detect(frame)
        detect_ms = (time.time() - t_detect) * 1000
        data_logger.info(
            f"detection/latest: detection completed in {detect_ms:.1f}ms, "
            f"{len(detections)} objects found",
            component="detection_route"
        )
    except MemoryError as e:
        detect_ms = (time.time() - t_detect) * 1000
        data_logger.critical(
            f"detection/latest: MemoryError after {detect_ms:.1f}ms during inference. "
            f"Image shape was {frame.shape}. Try a smaller image or restart the service.",
            component="detection_route",
            details=traceback.format_exc()
        )
        return jsonify({
            "error": "Out of memory during inference. Try a smaller image or restart the service.",
            "image_shape": list(frame.shape),
            "detection_time_ms": round(detect_ms, 1)
        }), 503
    except FileNotFoundError as e:
        detect_ms = (time.time() - t_detect) * 1000
        data_logger.critical(
            f"detection/latest: model file not found after {detect_ms:.1f}ms: {e}",
            component="detection_route",
            details=traceback.format_exc()
        )
        return jsonify({
            "error": f"Model file not found: {str(e)}",
            "hint": "Ensure yolov8n.onnx is in the project root"
        }), 500
    except Exception as e:
        detect_ms = (time.time() - t_detect) * 1000
        data_logger.error(
            f"detection/latest: detection failed after {detect_ms:.1f}ms: {e}",
            component="detection_route",
            details=traceback.format_exc()
        )
        return jsonify({
            "error": f"Detection failed: {str(e)}",
            "detection_time_ms": round(detect_ms, 1),
            "image_shape": list(frame.shape)
        }), 500

    # Step 5: Trigger event-based snapshot if objects detected
    if detections:
        t_event = time.time()
        try:
            check_detection_snapshot(detections)
            data_logger.debug(
                f"detection/latest: event snapshot check took {(time.time()-t_event)*1000:.1f}ms",
                component="detection_route"
            )
        except Exception as e:
            data_logger.error(
                f"detection/latest: event snapshot check failed: {e}",
                component="detection_route",
                details=traceback.format_exc()
            )
            # Don't fail the request — detection itself succeeded

    total_ms = (time.time() - t_start) * 1000
    data_logger.info(
        f"detection/latest: request completed in {total_ms:.1f}ms total",
        component="detection_route"
    )

    return jsonify({
        "capture": {
            "capture_id": capture.id,
            "filename": capture.filename,
            "filepath": capture.filepath,
            "created_at": capture.created_at.isoformat()
        },
        "detections": detections,
        "timing_ms": {
            "total": round(total_ms, 1),
            "detection": round(detect_ms, 1)
        }
    })


@ai_bp.route("/detection/image", methods=["GET"])
def detect_image():
    return jsonify({"message": "Not implemented yet"})