# app/__init__.py

import os
from flask import Flask, jsonify
from flask_cors import CORS

from app.extensions import db, jwt, bcrypt, socketio, limiter, migrate

from app.routes.api.v1.auth import auth_bp
from app.routes.api.v1.camera import camera_bp
from app.routes.api.v1.sensors import sensors_bp
from app.routes.api.v1.robot import robot_bp
from app.routes.api.v1.status import status_bp
from app.routes.api.v1.captures import captures_bp
from app.routes.api.v1.snapshots import snapshots_bp
from app.routes.api.v1.users import users_bp
from app.routes.api.v1.settings import settings_bp
from app.routes.api.v1.system import system_bp
from app.routes.api.v1.ai import ai_bp
from app.routes.api.v1.latency import latency_bp
from app.routes.api.v1.logs import logs_bp

from app.routes.control import control_bp
from app.routes.dashboard import dashboard_bp
from app.routes.sensors import sensors_page_bp
from app.routes.captures import captures_page_bp

from app.ai.detection.detector import ObjectDetector


def create_app():
    app = Flask(__name__)

    CORS(app,
         supports_credentials=True,
         origins=[
             "http://localhost:3000", "http://192.168.4.100:3000",
             "http://192.168.4.101:3000", "http://192.168.4.108:3000",
             "http://100.68.175.89:3000", "*"
         ])

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///robot.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["JWT_SECRET_KEY"] = os.environ.get(
        "JWT_SECRET_KEY",
        "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(
        os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 86400))

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    socketio.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    # Health check
    @app.route("/api/v1/health", methods=["GET"])
    @limiter.limit("60/minute")
    def health_check():
        from app.services.sensor_stream import manager as sensor_manager
        from app.services.latency_monitor import monitor as latency_monitor
        from app.services.data_logger import data_logger as logger

        sensor_health = sensor_manager.get_health()
        latency_stats = latency_monitor.get_current_stats(window_seconds=60)
        log_stats = logger.get_stats(hours=1)

        # Determine overall status
        issues = []
        if sensor_health["consecutive_db_errors"] > 5:
            issues.append("High consecutive DB errors")
        if sensor_health["buffered_writes"] > 50:
            issues.append("Large write buffer backlog")
        if latency_stats.get("avg_ms") and latency_stats["avg_ms"] > 1000:
            issues.append("High average latency")

        overall_status = "ok" if not issues else "degraded"

        return jsonify({
            "status": overall_status,
            "service": "robot-control-api",
            "version": "1.0.0",
            "issues": issues,
            "sensor_stream": sensor_health,
            "latency": {
                "avg_ms": latency_stats.get("avg_ms"),
                "p95_ms": latency_stats.get("p95_ms"),
                "current_ms": latency_stats.get("current_ms"),
            },
            "logs_last_hour": log_stats,
        })

    # API v1 routes
    app.register_blueprint(auth_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(sensors_bp)
    app.register_blueprint(robot_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(captures_bp)
    app.register_blueprint(snapshots_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(latency_bp)
    app.register_blueprint(logs_bp)

    # HTML frontend routes
    app.register_blueprint(control_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sensors_page_bp)
    app.register_blueprint(captures_page_bp)

    # Register latency tracking middleware
    from app.middleware.latency import register_latency_middleware
    register_latency_middleware(app)

    with app.app_context():
        db.create_all()

    detector = ObjectDetector()
    detector.load()

    return app
