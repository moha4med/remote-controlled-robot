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
from app.routes.api.v1.users import users_bp
from app.routes.api.v1.settings import settings_bp
from app.routes.api.v1.history_logs import history_logs_bp
from app.routes.api.v1.hourly_history import hourly_history_bp
from app.routes.api.v1.system import system_bp
from app.routes.api.v1.ai import ai_bp

from app.routes.control import control_bp
from app.routes.dashboard import dashboard_bp
from app.routes.sensors import sensors_page_bp


def create_app():
    app = Flask(__name__)

    CORS(app, supports_credentials=True, origins=[
        "http://localhost:3000",
        "http://192.168.4.100:3000",
        "http://192.168.4.108:3000",
        "*"
    ])

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///robot.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["JWT_SECRET_KEY"] = os.environ.get(
        "JWT_SECRET_KEY",
        "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
    )
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(os.environ.get(
        "JWT_ACCESS_TOKEN_EXPIRES", 86400
    ))

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
        return jsonify({
            "status": "ok",
            "service": "robot-control-api",
            "version": "1.0.0",
        })

    # API v1 routes
    app.register_blueprint(auth_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(sensors_bp)
    app.register_blueprint(robot_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(captures_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(history_logs_bp)
    app.register_blueprint(hourly_history_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(ai_bp)

    # HTML frontend routes
    app.register_blueprint(control_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sensors_page_bp)

    with app.app_context():
        db.create_all()

    return app