# app/routes/api/v1/auth.py
# API routes for user authentication, including login, token refresh, and user info retrieval. Uses JWT for stateless authentication.

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from datetime import timedelta
from app.extensions import bcrypt, limiter
from app.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    data = request.json

    username = data.get("username")
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    if not bcrypt.check_password_hash(user.password_hash, data["password"]):
        return jsonify({"message": "Invalid credentials"}), 401

    remember_me = data.get("remember_me", False)
    expires = timedelta(days=30) if remember_me else timedelta(hours=1)

    access_token = create_access_token(identity=str(user.id), expires_delta=expires)
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
        },
    })


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
@limiter.limit("30/minute")
def refresh():
    """Refresh an expired access token using a valid refresh token."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user or not user.is_active:
        return jsonify({"message": "User not found or inactive"}), 401

    new_access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "access_token": new_access_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
        },
    })


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
@limiter.limit("30/minute")
def me():
    user_id = int(get_jwt_identity())

    user = User.query.get(user_id)

    return jsonify({
        "status": "success",
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
        }
    })


@auth_bp.route("/logout", methods=["POST"])
@limiter.limit("10/minute")
def logout():
    return jsonify({"message": "Logged out successfully"})