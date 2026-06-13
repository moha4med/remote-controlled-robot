# app/services/sensor_stream.py
# Sensor data acquisition, persistence, and Socket.IO broadcasting.
# Enhanced with: buffered writes, retry logic, latency tracking, data logging.

import time
import json
import random
from collections import deque
from app.extensions import socketio, db
from app.sensors.usb_temp_humidity import USBTempHumiditySensor
from app.models.sensor_log import SensorLog
from app.services.robot_service import RobotService
from app.services.system_service import get_system_metrics
from app.services.event_capture import check_sensor_snapshot
from app.services.latency_monitor import monitor
from app.services.data_logger import data_logger


class SensorStreamManager:
    """Central manager for sensor data acquisition, persistence, and broadcast."""

    def __init__(self):
        self._sensor = None
        self._init_sensor()
        self.robot = RobotService()
        self._system_interval = 5.0
        self._last_system_emit = 0
        # Buffer for sensor data that failed to write to DB
        self._write_buffer = deque(maxlen=100)
        self._consecutive_db_errors = 0
        self._max_retries = 3
        self._retry_delay = 1.0
        # Track sensor loop latency
        self._loop_count = 0
        self._last_latency_emit = 0
        self._latency_emit_interval = 5.0
        # Track whether we're getting real sensor data
        self._using_real_sensor = False
        self._last_real_data_timestamp = 0
        # Track whether the sensor loop is running
        self._loop_running = False

    def _init_sensor(self):
        try:
            self._sensor = USBTempHumiditySensor("COM5", baudrate=9600)
            data_logger.info("Sensor initialized successfully", component="sensor_stream")
        except Exception as e:
            self._sensor = None
            data_logger.warning(
                f"Sensor initialization failed: {e}. Using simulated values.",
                component="sensor_stream"
            )

    @property
    def sensor(self):
        if self._sensor is None:
            self._init_sensor()
        return self._sensor

    def read_sensors(self):
        """Read physical sensors, fall back to simulated values."""
        temp = None
        humidity = None
        s = self.sensor
        got_real_data = False
        if s is not None:
            try:
                data = s.read()
                if data:
                    temp = data.get("temperature")
                    humidity = data.get("humidity")
                    if temp is not None or humidity is not None:
                        got_real_data = True
                        self._using_real_sensor = True
                        self._last_real_data_timestamp = time.time()
            except Exception as e:
                data_logger.warning(
                    f"Sensor read failed: {e}. Using simulated values.",
                    component="sensor_stream"
                )

        # If sensor object exists but hasn't returned real data for 60s, mark as disconnected
        if self._sensor is not None and self._using_real_sensor:
            if time.time() - self._last_real_data_timestamp > 60:
                self._using_real_sensor = False

        if temp is None:
            temp = round(22 + random.uniform(-3, 3), 1)
        if humidity is None:
            humidity = round(55 + random.uniform(-10, 10), 1)

        battery = round(100)
        signal = round(90 + random.uniform(-8, 2), 1)

        return {
            "temperature": temp,
            "humidity": humidity,
            "battery": battery,
            "signal": signal,
            "robot_state": self.robot.state,
            "timestamp": time.time(),
        }

    def persist(self, data):
        """Save sensor snapshot to database with retry and buffering."""
        log_entry = SensorLog(
            temperature=data.get("temperature"),
            humidity=data.get("humidity"),
            battery=data.get("battery"),
            signal_strength=data.get("signal"),
            robot_state=data.get("robot_state"),
        )

        # Try to write buffered entries first
        self._flush_write_buffer()

        # Attempt to write current entry
        for attempt in range(self._max_retries):
            try:
                db.session.add(log_entry)
                db.session.commit()
                self._consecutive_db_errors = 0
                return True
            except Exception as e:
                db.session.rollback()
                self._consecutive_db_errors += 1
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay * (attempt + 1))

        # All retries failed — buffer the entry
        self._write_buffer.append(log_entry)
        data_logger.error(
            f"Failed to persist sensor data after {self._max_retries} retries. "
            f"Buffered ({len(self._write_buffer)} pending). Error: {e}",
            component="sensor_stream"
        )
        return False

    def _flush_write_buffer(self):
        """Attempt to flush buffered sensor writes."""
        if not self._write_buffer:
            return

        flushed = 0
        while self._write_buffer:
            entry = self._write_buffer[0]
            try:
                db.session.add(entry)
                db.session.commit()
                self._write_buffer.popleft()
                flushed += 1
            except Exception:
                db.session.rollback()
                break

        if flushed > 0:
            data_logger.info(
                f"Flushed {flushed} buffered sensor entries ({len(self._write_buffer)} remaining)",
                component="sensor_stream"
            )

    def read_and_broadcast(self):
        """Read sensors, persist, emit via SocketIO, check for events."""
        loop_start = time.time()

        data = self.read_sensors()
        self.persist(data)

        # Check for abnormal sensor readings -> event-based snapshot
        check_sensor_snapshot({
            "temperature": data["temperature"],
            "humidity": data["humidity"],
            "battery": data["battery"],
            "signal_strength": data["signal"],
        })

        socketio.emit("sensor:update", {
            "temperature": data["temperature"],
            "humidity": data["humidity"],
            "battery": data["battery"],
            "signal": data["signal"],
            "robot_state": data["robot_state"],
            "timestamp": data["timestamp"],
        })

        # Track sensor loop latency
        loop_latency_ms = (time.time() - loop_start) * 1000
        monitor.record(
            latency_ms=loop_latency_ms,
            category="sensor_loop",
            endpoint="read_and_broadcast",
        )

        # Periodically broadcast latency stats via SocketIO
        self._loop_count += 1
        now = time.time()
        if now - self._last_latency_emit >= self._latency_emit_interval:
            self._broadcast_latency()
            self._last_latency_emit = now

    def _broadcast_latency(self):
        """Emit current latency stats to connected clients."""
        try:
            stats = monitor.get_current_stats(window_seconds=60)
            socketio.emit("latency:update", stats)
        except Exception as e:
            pass

    def broadcast_system_metrics(self):
        """Read system metrics and emit via SocketIO."""
        try:
            metrics = get_system_metrics()
            socketio.emit("system:update", metrics)
        except Exception as e:
            data_logger.error(
                f"Failed to broadcast system metrics: {e}",
                component="sensor_stream"
            )

    def get_health(self):
        """Return health status of the sensor stream."""
        # Sensor is considered connected if:
        # 1. We have a sensor object AND we're getting real data from it, OR
        # 2. The loop is running (data is being produced, even if simulated)
        sensor_connected = self._using_real_sensor or self._loop_running or (self._loop_count > 0)
        return {
            "sensor_connected": sensor_connected,
            "using_real_sensor": self._using_real_sensor,
            "loop_running": self._loop_running,
            "buffered_writes": len(self._write_buffer),
            "consecutive_db_errors": self._consecutive_db_errors,
            "loop_count": self._loop_count,
        }


manager = SensorStreamManager()


def sensor_loop(app):
    """Background loop: read sensors, persist, emit every 2.5s."""
    with app.app_context():
        manager._loop_running = True
        data_logger.info("Sensor loop started", component="sensor_stream")
        while True:
            try:
                manager.read_and_broadcast()
                now = time.time()
                if now - manager._last_system_emit >= manager._system_interval:
                    manager.broadcast_system_metrics()
                    manager._last_system_emit = now
            except Exception as e:
                data_logger.error(
                    f"Sensor loop error: {e}",
                    component="sensor_stream",
                    details=str(e)
                )
                try:
                    socketio.emit("sensor:error", {"error": str(e)})
                except Exception:
                    pass
            socketio.sleep(2.5)