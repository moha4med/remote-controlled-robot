# app/routes/api/v1/captures.py
# API for camera capture listing, trigger, and file serving

import os
from flask import Blueprint, jsonify, send_file, request
from app.sensors.camera import camera, BASE_DIR
from app.extensions import db
from app.models.capture import Capture

captures_bp = Blueprint("captures", __name__, url_prefix="/api/v1/captures")

CAPTURES_DIR = os.path.join(BASE_DIR, "app", "static", "captures")


def _get_base_url():
    """Build the base URL from the request, respecting reverse proxies."""
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{scheme}://{host}"


@captures_bp.route("/", methods=["GET"])
def list_captures():
    """Return the latest 50 captures, newest first."""
    captures = (
        Capture.query
        .order_by(Capture.created_at.desc())
        .limit(50)
        .all()
    )
    base_url = _get_base_url()
    return jsonify([c.to_dict(base_url=base_url) for c in captures])


@captures_bp.route("/", methods=["POST"])
def trigger_capture():
    """Capture an image, persist metadata to DB, return the record."""
    result = camera.capture_image()

    capture = Capture(
        filename=result["filename"],
        filepath=result["filepath"],
        thumbnail_path=result["thumbnail_path"],
        file_size=result["file_size"],
        width=result["width"],
        height=result["height"],
    )
    db.session.add(capture)
    db.session.commit()

    base_url = _get_base_url()
    return jsonify(capture.to_dict(base_url=base_url)), 201


@captures_bp.route("/file/<path:filename>")
def serve_file(filename):
    """Serve a full-resolution capture image."""
    safe_path = os.path.join(CAPTURES_DIR, filename)
    # Basic path traversal protection
    if not os.path.realpath(safe_path).startswith(os.path.realpath(CAPTURES_DIR)):
        return jsonify({"error": "Invalid path"}), 403
    if not os.path.exists(safe_path):
        return jsonify({"error": "File not found"}), 404
    return send_file(safe_path, mimetype="image/jpeg")


@captures_bp.route("/thumb/<path:filename>")
def serve_thumbnail(filename):
    """Serve a thumbnail image."""
    thumb_dir = os.path.join(CAPTURES_DIR, "thumbs")
    thumb_filename = f"thumb_{filename.replace('capture_', '')}"
    safe_path = os.path.join(thumb_dir, thumb_filename)
    if not os.path.realpath(safe_path).startswith(os.path.realpath(CAPTURES_DIR)):
        return jsonify({"error": "Invalid path"}), 403
    if not os.path.exists(safe_path):
        return jsonify({"error": "Thumbnail not found"}), 404
    return send_file(safe_path, mimetype="image/jpeg")


@captures_bp.route("/latest", methods=["GET"])
def latest_capture():
    """Return the most recent capture record (no file download)."""
    capture = Capture.query.order_by(Capture.created_at.desc()).first()
    if not capture:
        return jsonify({"message": "No captures yet"}), 404
    base_url = _get_base_url()
    return jsonify(capture.to_dict(base_url=base_url))