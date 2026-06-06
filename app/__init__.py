# app/__init__.py

from flask import Flask
from flask_cors import CORS

from app.extensions import db, jwt, bcrypt, socketio, limiter

from app.routes.api.v1.auth import auth_bp
from app.routes.api.v1.camera import camera_bp
from app.routes.api.v1.sensors import sensors_bp
from app.routes.api.v1.robot import robot_bp
from app.routes.api.v1.status import status_bp
from app.routes.api.v1.logs import logs_bp
from app.routes.api.v1.captures import captures_bp
from app.routes.api.v1.users import users_bp
from app.routes.api.v1.settings import settings_bp
from app.routes.control import control_bp
from app.routes.dashboard import dashboard_bp
from app.routes.sensors import sensors_page_bp


def create_app():
    app = Flask(__name__)

    CORS(app, supports_credentials=True, origins=[
        "http://localhost:3000",
        "http://192.168.4.100:3000"
    ])

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///robot.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["JWT_SECRET_KEY"] = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 86400  # 24 hours

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    socketio.init_app(app)
    limiter.init_app(app)

    # API v1 routes
    app.register_blueprint(auth_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(sensors_bp)
    app.register_blueprint(robot_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(captures_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)

    # HTML frontend routes
    app.register_blueprint(control_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sensors_page_bp)

    with app.app_context():
        db.create_all()

    return app