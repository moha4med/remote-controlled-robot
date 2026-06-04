from flask import Blueprint, jsonify
from app.sensors.usb_temp_humidity import USBTempHumiditySensor

sensors_bp = Blueprint("sensors", __name__, url_prefix="/api/v1/sensors")

sensor = USBTempHumiditySensor("/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0")

@sensors_bp.route("/sensors", methods=["GET"])
def environment():
    data = sensor.read()
    return jsonify(data)
