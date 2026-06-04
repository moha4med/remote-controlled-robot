import serial
import re

class USBTempHumiditySensor:
    def __init__(self, port="COM5", baudrate=9600):
        self.ser = serial.Serial(port, baudrate, timeout=1)

    def read_raw(self):
        line = self.ser.readline().decode(errors="ignore").strip()
        return line

    def read(self):
        line = self.read_raw()

        match = re.search(r"T:\s*([0-9.]+),\s*RH:\s*([0-9.]+)", line)
        if not match:
            return None

        temp = float(match.group(1))
        humidity = float(match.group(2)) * 100  # convert to %

        return {
            "temperature": round(temp, 2),
            "humidity": round(humidity, 2),
            "raw": line
        }
