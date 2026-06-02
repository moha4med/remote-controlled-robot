# app/__init__.py

from flask import Flask

from app.extensions import db
from app.extensions import jwt
from app.extensions import bcrypt

from app.routes.video import video_bp
from app.routes.robot import robot_bp

def create_app():
    app = Flask(__name__)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///robot.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    app.config["JWT_SECRET_KEY"] = ""
    
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)

    app.register_blueprint(video_bp)
    app.register_blueprint(robot_bp, url_prefix="/api/robot")
    
    with app.app_context():
        db.create_all()

    return app
