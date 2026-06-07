from flask import Blueprint, jsonify
from app.extensions import limiter
from app.sensors.usb_temp_humidity import USBTempHumiditySensor

sensors_bp = Blueprint("sensors_api", __name__, url_prefix="/api/v1/sensors")

sensor = USBTempHumiditySensor("/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0")


@sensors_bp.route("/", methods=["GET"])
@limiter.limit("60/minute")
# @jwt_required_role("operator")  # uncomment to enable auth
def environment():
    """Return current environment sensor readings."""
    data = sensor.read()
    return jsonify(data)