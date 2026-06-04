import time
from app.extensions import socketio
from app.sensors.usb_temp_humidity import USBTempHumiditySensor

sensor = USBTempHumiditySensor("/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0")

def sensor_loop():
    while True:
        try:
            data = sensor.read()

            socketio.emit("sensor:update", {
                "temp": data.get("temperature"),
                "humidity": data.get("humidity"),
                "timestamp": time.time()
            })

        except Exception as e:
            socketio.emit("sensor:error", {"error": str(e)})

        socketio.sleep(2.5)
        