# app/services/event_capture.py
# Event-based snapshot capture service
# Triggers snapshots when abnormal sensor readings or detection events occur

import json
import threading
import os
import cv2
from datetime import datetime, timezone

from app.extensions import db, socketio
from app.models.snapshot import Snapshot
from app.sensors.camera import camera
from app.services.data_logger import data_logger

# Thresholds for event-based capture
THRESHOLDS = {
    "temperature_high": 45.0,
    "temperature_low": -10.0,
    "humidity_high": 95.0,
    "humidity_low": 10.0,
    "battery_low": 15.0,
    "signal_weak": -85.0,
}

# Cooldown per event type (seconds) — prevents snapshot spam
COOLDOWN = 30
_event_timers = {}
_timer_lock = threading.Lock()

BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app",
    "static", "snapshots")


def _is_on_cooldown(event_type):
    with _timer_lock:
        last_time = _event_timers.get(event_type)
        if last_time is None:
            return False
        elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
        return elapsed < COOLDOWN


def _set_cooldown(event_type):
    with _timer_lock:
        _event_timers[event_type] = datetime.now(timezone.utc)


def _save_event_snapshot(source, event_type, description, context):
    try:
        frame = camera._capture_frame()
        h, w = frame.shape[:2]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"snapshot_{timestamp}.jpg"
        thumb_filename = f"thumb_{timestamp}.jpg"

        save_dir = BASE_DIR
        thumb_dir = os.path.join(save_dir, "thumbs")
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(thumb_dir, exist_ok=True)

        full_path = os.path.join(save_dir, filename)
        thumb_path = os.path.join(thumb_dir, thumb_filename)

        cv2.imwrite(full_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

        thumb_w = 320
        thumb_h = int(h * (thumb_w / w))
        thumb = cv2.resize(frame, (thumb_w, thumb_h),
                           interpolation=cv2.INTER_AREA)
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
            context_json=json.dumps({
                "description": description,
                "context": context
            }),
        )
        db.session.add(snapshot)
        db.session.commit()

        # Notify connected clients via Socket.IO
        socketio.emit(
            "snapshot:event", {
                "source": source,
                "event_type": event_type,
                "description": description,
                "filename": filename,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        print(f"[EVENT_CAPTURE] {event_type}: {description} -> {filename}")
    except Exception as e:
        print(f"[EVENT_CAPTURE] Failed: {e}")


def check_sensor_snapshot(sensor_data):
    """Check sensor readings against thresholds and trigger snapshot if abnormal."""
    events = []

    temp = sensor_data.get("temperature")
    if temp is not None:
        if temp > THRESHOLDS["temperature_high"]:
            events.append(
                ("high_temperature", f"Temperature {temp}C exceeds threshold"))
        elif temp < THRESHOLDS["temperature_low"]:
            events.append(
                ("low_temperature", f"Temperature {temp}C below threshold"))

    humidity = sensor_data.get("humidity")
    if humidity is not None:
        if humidity > THRESHOLDS["humidity_high"]:
            events.append(
                ("high_humidity", f"Humidity {humidity}% exceeds threshold"))
        elif humidity < THRESHOLDS["humidity_low"]:
            events.append(
                ("low_humidity", f"Humidity {humidity}% below threshold"))

    battery = sensor_data.get("battery")
    if battery is not None and battery < THRESHOLDS["battery_low"]:
        events.append(("low_battery", f"Battery {battery}% below threshold"))

    signal = sensor_data.get("signal_strength")
    if signal is not None and signal < THRESHOLDS["signal_weak"]:
        events.append(("weak_signal", f"Signal {signal}dBm below threshold"))

    for event_type, description in events:
        if not _is_on_cooldown(event_type):
            _save_event_snapshot("event", event_type, description, sensor_data)
            _set_cooldown(event_type)


def check_detection_snapshot(detections):
    """Trigger snapshot when objects are detected by the AI detector."""
    if not detections:
        data_logger.debug(
            "check_detection_snapshot: no detections, skipping",
            component="event_capture"
        )
        return

    high_conf = [d for d in detections if d.get("confidence", 0) > 0.6]
    data_logger.debug(
        f"check_detection_snapshot: {len(detections)} total detections, "
        f"{len(high_conf)} high-confidence (>0.6)",
        component="event_capture"
    )

    if not high_conf:
        data_logger.debug(
            "check_detection_snapshot: no high-confidence detections, skipping",
            component="event_capture"
        )
        return

    event_type = "object_detected"
    if _is_on_cooldown(event_type):
        data_logger.debug(
            f"check_detection_snapshot: '{event_type}' on cooldown, skipping",
            component="event_capture"
        )
        return

    labels = ", ".join(d["label"] for d in high_conf)
    data_logger.info(
        f"check_detection_snapshot: triggering snapshot for '{labels}' "
        f"({len(high_conf)} objects)",
        component="event_capture"
    )
    _save_event_snapshot("detection", event_type, f"Detected: {labels}",
                         {"detections": detections})
    _set_cooldown(event_type)
