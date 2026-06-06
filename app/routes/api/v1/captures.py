# app/routes/api/v1/captures.py
# API for camera capture listing, trigger, delete, and file serving

import os
from flask import Blueprint, jsonify, send_file, request, make_response
from app.sensors.camera import camera, BASE_DIR
from app.extensions import db, limiter
from app.models.capture import Capture
from app.middleware.auth import jwt_required_role

captures_bp = Blueprint("captures", __name__, url_prefix="/api/v1/captures")

CAPTURES_DIR = os.path.join(BASE_DIR, "app", "static", "captures")


def _get_base_url():
    """Build the base URL from the request, respecting reverse proxies."""
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{scheme}://{host}"


def _add_cors(response):
    """Add CORS headers to a response."""
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@captures_bp.route("/", methods=["GET"])
@limiter.limit("30/minute")
def list_captures():
    """Return captures with pagination, search, and date filtering."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 12, type=int)
    search = request.args.get("search", "", type=str)
    date_from = request.args.get("date_from", "", type=str)
    date_to = request.args.get("date_to", "", type=str)

    query = Capture.query

    if search:
        query = query.filter(Capture.filename.ilike(f"%{search}%"))

    if date_from:
        try:
            from datetime import datetime
            df = datetime.fromisoformat(date_from)
            query = query.filter(Capture.created_at >= df)
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime, timedelta
            dt = datetime.fromisoformat(date_to)
            dt = dt + timedelta(days=1)
            query = query.filter(Capture.created_at < dt)
        except ValueError:
            pass

    total = query.count()
    captures = (
        query
        .order_by(Capture.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    base_url = _get_base_url()

    response = make_response(jsonify({
        "items": [c.to_dict(base_url=base_url) for c in captures],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }))
    return _add_cors(response)


@captures_bp.route("/", methods=["POST"])
# @jwt_required_role("operator")
@limiter.limit("10/minute")
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
    response = make_response(jsonify(capture.to_dict(base_url=base_url)), 201)
    return _add_cors(response)


@captures_bp.route("/<int:capture_id>", methods=["DELETE"])
# @jwt_required_role("operator")
@limiter.limit("10/minute")
def delete_capture(capture_id):
    """Delete a capture record and its associated files."""
    capture = Capture.query.get_or_404(capture_id)

    try:
        if capture.filepath and os.path.exists(capture.filepath):
            os.remove(capture.filepath)
    except OSError:
        pass

    try:
        if capture.thumbnail_path and os.path.exists(capture.thumbnail_path):
            os.remove(capture.thumbnail_path)
    except OSError:
        pass

    db.session.delete(capture)
    db.session.commit()

    response = make_response(jsonify({"message": "Capture deleted", "id": capture_id}), 200)
    return _add_cors(response)


@captures_bp.route("/file/<path:filename>")
@limiter.limit("60/minute")
def serve_file(filename):
    """Serve a full-resolution capture image with CORS headers."""
    safe_path = os.path.join(CAPTURES_DIR, filename)
    if not os.path.realpath(safe_path).startswith(os.path.realpath(CAPTURES_DIR)):
        response = make_response(jsonify({"error": "Invalid path"}), 403)
        return _add_cors(response)
    if not os.path.exists(safe_path):
        response = make_response(jsonify({"error": "File not found"}), 404)
        return _add_cors(response)
    response = make_response(send_file(safe_path, mimetype="image/jpeg"))
    return _add_cors(response)


@captures_bp.route("/thumb/<path:filename>")
@limiter.limit("60/minute")
def serve_thumbnail(filename):
    """Serve a thumbnail image with CORS headers."""
    thumb_dir = os.path.join(CAPTURES_DIR, "thumbs")
    thumb_filename = f"thumb_{filename.replace('capture_', '')}"
    safe_path = os.path.join(thumb_dir, thumb_filename)
    if not os.path.realpath(safe_path).startswith(os.path.realpath(CAPTURES_DIR)):
        response = make_response(jsonify({"error": "Invalid path"}), 403)
        return _add_cors(response)
    if not os.path.exists(safe_path):
        response = make_response(jsonify({"error": "Thumbnail not found"}), 404)
        return _add_cors(response)
    response = make_response(send_file(safe_path, mimetype="image/jpeg"))
    return _add_cors(response)


@captures_bp.route("/latest", methods=["GET"])
@limiter.limit("30/minute")
def latest_capture():
    """Return the most recent capture record (no file download)."""
    capture = Capture.query.order_by(Capture.created_at.desc()).first()
    if not capture:
        response = make_response(jsonify({"message": "No captures yet"}), 404)
        return _add_cors(response)
    base_url = _get_base_url()
    response = make_response(jsonify(capture.to_dict(base_url=base_url)))
    return _add_cors(response)