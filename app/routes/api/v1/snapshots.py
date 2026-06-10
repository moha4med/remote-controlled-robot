# app/routes/api/v1/snapshots.py
# API for video stream snapshots — manual capture, event-based, listing, and serving

import os
import json
from flask import Blueprint, jsonify, send_file, request, make_response
from app.sensors.camera import camera
from app.extensions import db, limiter
from app.models.snapshot import Snapshot
from app.middleware.auth import jwt_required_role
from datetime import datetime

snapshots_bp = Blueprint("snapshots", __name__, url_prefix="/api/v1/snapshots")

SNAPSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "app", "static", "snapshots"
)


def _get_base_url():
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{scheme}://{host}"


def _add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@snapshots_bp.route("/", methods=["GET"])
@limiter.limit("30/minute")
def list_snapshots():
    """Return snapshots with pagination, filtering by source, and date range."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 12, type=int)
    source = request.args.get("source", "", type=str)
    event_type = request.args.get("event_type", "", type=str)
    date_from = request.args.get("date_from", "", type=str)
    date_to = request.args.get("date_to", "", type=str)

    query = Snapshot.query

    if source:
        query = query.filter_by(source=source)
    if event_type:
        query = query.filter_by(event_type=event_type)
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.filter(Snapshot.created_at >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            from datetime import timedelta
            dt = dt + timedelta(days=1)
            query = query.filter(Snapshot.created_at < dt)
        except ValueError:
            pass

    total = query.count()
    snapshots = (
        query
        .order_by(Snapshot.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    base_url = _get_base_url()

    response = make_response(jsonify({
        "items": [s.to_dict(base_url=base_url) for s in snapshots],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }))
    return _add_cors(response)


@snapshots_bp.route("/", methods=["POST"])
@limiter.limit("20/minute")
def create_snapshot():
    """Capture a snapshot from the live stream and save to disk.

    Accepts optional JSON body:
        - source: "manual" | "event" | "detection" (default: "manual")
        - event_type: string description (e.g. "high_temperature", "object_detected")
        - context: JSON-serializable dict with extra context
    """
    data = request.json or {}
    source = data.get("source", "manual")
    event_type = data.get("event_type", None)
    context = data.get("context", None)

    # Validate source
    if source not in ("manual", "event", "detection"):
        source = "manual"

    # Capture frame from camera
    result = camera.capture_image(jpeg_quality=85)

    # Override filename to use snapshot prefix
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"snapshot_{timestamp}.jpg"
    thumb_filename = f"thumb_{timestamp}.jpg"

    save_dir = SNAPSHOTS_DIR
    thumb_dir = os.path.join(save_dir, "thumbs")
    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(thumb_dir, exist_ok=True)

    import cv2
    frame = camera._capture_frame()
    h, w = frame.shape[:2]

    full_path = os.path.join(save_dir, filename)
    thumb_path = os.path.join(thumb_dir, thumb_filename)

    cv2.imwrite(full_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

    thumb_w = 320
    thumb_h = int(h * (thumb_w / w))
    thumb = cv2.resize(frame, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
    cv2.imwrite(thumb_path, thumb, [cv2.IMWRITE_JPEG_QUALITY, 65])

    snapshot = Snapshot(
        filename=filename,
        filepath=full_path,
        thumbnail_path=thumb_path,
        file_size=os.path.getsize(full_path),
        width=w,
        height=h,
        source=source,
        event_type=event_type,
        context_json=json.dumps(context) if context else None,
    )
    db.session.add(snapshot)
    db.session.commit()

    base_url = _get_base_url()
    response = make_response(jsonify(snapshot.to_dict(base_url=base_url)), 201)
    return _add_cors(response)


@snapshots_bp.route("/<int:snapshot_id>", methods=["DELETE"])
@limiter.limit("10/minute")
def delete_snapshot(snapshot_id):
    """Delete a snapshot record and its associated files."""
    snapshot = Snapshot.query.get_or_404(snapshot_id)

    try:
        if snapshot.filepath and os.path.exists(snapshot.filepath):
            os.remove(snapshot.filepath)
    except OSError:
        pass

    try:
        if snapshot.thumbnail_path and os.path.exists(snapshot.thumbnail_path):
            os.remove(snapshot.thumbnail_path)
    except OSError:
        pass

    db.session.delete(snapshot)
    db.session.commit()

    response = make_response(jsonify({"message": "Snapshot deleted", "id": snapshot_id}), 200)
    return _add_cors(response)


@snapshots_bp.route("/file/<path:filename>")
@limiter.limit("60/minute")
def serve_file(filename):
    """Serve a full-resolution snapshot image."""
    safe_path = os.path.join(SNAPSHOTS_DIR, filename)
    if not os.path.realpath(safe_path).startswith(os.path.realpath(SNAPSHOTS_DIR)):
        response = make_response(jsonify({"error": "Invalid path"}), 403)
        return _add_cors(response)
    if not os.path.exists(safe_path):
        response = make_response(jsonify({"error": "File not found"}), 404)
        return _add_cors(response)
    response = make_response(send_file(safe_path, mimetype="image/jpeg"))
    return _add_cors(response)


@snapshots_bp.route("/thumb/<path:filename>")
@limiter.limit("60/minute")
def serve_thumbnail(filename):
    """Serve a thumbnail image."""
    thumb_dir = os.path.join(SNAPSHOTS_DIR, "thumbs")
    thumb_filename = f"thumb_{filename.replace('snapshot_', '')}"
    safe_path = os.path.join(thumb_dir, thumb_filename)
    if not os.path.realpath(safe_path).startswith(os.path.realpath(SNAPSHOTS_DIR)):
        response = make_response(jsonify({"error": "Invalid path"}), 403)
        return _add_cors(response)
    if not os.path.exists(safe_path):
        response = make_response(jsonify({"error": "Thumbnail not found"}), 404)
        return _add_cors(response)
    response = make_response(send_file(safe_path, mimetype="image/jpeg"))
    return _add_cors(response)


@snapshots_bp.route("/latest", methods=["GET"])
@limiter.limit("30/minute")
def latest_snapshot():
    """Return the most recent snapshot."""
    snapshot = Snapshot.query.order_by(Snapshot.created_at.desc()).first()
    if not snapshot:
        response = make_response(jsonify({"message": "No snapshots yet"}), 404)
        return _add_cors(response)
    base_url = _get_base_url()
    response = make_response(jsonify(snapshot.to_dict(base_url=base_url)))
    return _add_cors(response)


@snapshots_bp.route("/stats", methods=["GET"])
@limiter.limit("30/minute")
def snapshot_stats():
    """Return snapshot counts by source."""
    from sqlalchemy import func

    counts = (
        db.session.query(Snapshot.source, func.count(Snapshot.id))
        .group_by(Snapshot.source)
        .all()
    )

    stats = {source: count for source, count in counts}
    stats["total"] = sum(stats.values())

    response = make_response(jsonify(stats))
    return _add_cors(response)