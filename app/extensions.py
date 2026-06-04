# app/extensions

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO

socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="threading"
)

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
socketio = SocketIO(cors_allowed_origins="*")
