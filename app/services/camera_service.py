# app/services/camera_service.py
#
# MJPEG stream generator.
# The camera singleton already pre-encodes frames as JPEG bytes in a
# background thread. This service simply yields them in the MJPEG format
# and calls `camera.release()` when streaming stops.

import time
from app.sensors.camera import camera


def generate_stream():
    """Generator that yields MJPEG frames from the shared camera buffer.

    The camera runs at ~10 fps when readers are active and drops to ~2 fps
    when idle.  Each frame is already JPEG-encoded, so there is no per-frame
    encode overhead.

    Yields:
        bytes: a multipart/x-mixed-replace chunk containing a JPEG frame.
    """
    try:
        while True:
            frame_bytes = camera.get_frame()
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
            )
            time.sleep(0.05)
    except GeneratorExit:
        pass
    finally:
        camera.release()