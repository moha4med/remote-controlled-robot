# app/__init__.py

from flask import Flask
from flask_cors import CORS

from app.extensions import db
from app.extensions import jwt
from app.extensions import bcrypt
from app.extensions import socketio

from app.routes.api.v1.auth import auth_bp
from app.routes.api.v1.camera import camera_bp
from app.routes.api.v1.sensors import sensors_bp
# from app.routes.api.v1.robot import robot_bp

def create_app():
    app = Flask(__name__)
    
    CORS(app, supports_credentials=True, origins=[
        "http://localhost:3000",
        "http://192.168.4.100:3000"
    ])
    
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///robot.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    app.config["JWT_SECRET_KEY"] = "test-secret-key"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600
    
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    socketio.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(sensors_bp)
    # app.register_blueprint(robot_bp)
    
    with app.app_context():
        db.create_all()

    return app
