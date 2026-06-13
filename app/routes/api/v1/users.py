# app/routes/api/v1/users.py
# Full CRUD API for user management (admin only)

from flask import Blueprint, request, jsonify
from app.extensions import db, bcrypt, limiter
from app.models.user import User
from app.middleware.auth import jwt_required_role

users_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


@users_bp.route("/", methods=["GET"])
@jwt_required_role("admin")
@limiter.limit("30/minute")
def list_users():
    """Return all users."""
    users = User.query.order_by(User.created_at.desc()).all()
    
    return jsonify({
        "status": "success",
        "data": [u.to_dict() for u in users],
    })


@users_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required_role("admin")
@limiter.limit("30/minute")
def get_user(user_id):
    """Return a single user by ID."""
    user = User.query.get_or_404(user_id)
    
    return jsonify({
        "status": "success",
        "data": user.to_dict(),
    })


@users_bp.route("/", methods=["POST"])
@jwt_required_role("admin")
@limiter.limit("10/minute")
def create_user():
    """Create a new user."""
    data = request.json or {}

    if not data.get("username"):
        return jsonify({"status": "error", "message": "Username is required"}), 400
    if not data.get("first_name"):
        return jsonify({"status": "error", "message": "First name is required"}), 400
    if not data.get("last_name"):
        return jsonify({"status": "error", "message": "Last name is required"}), 400
    if not data.get("email"):
        return jsonify({"status": "error", "message": "Email is required"}), 400
    if not data.get("password"):
        return jsonify({"status": "error", "message": "Password is required"}), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"status": "error", "message": "Username already exists"}), 409
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"status": "error", "message": "Email already exists"}), 409

    hashed = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

    user = User(
        username=data["username"],
        email=data["email"],
        password_hash=hashed,
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        role=data.get("role", "operator"),
        is_active=data.get("is_active", True),
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "User created successfully",
        "data": user.to_dict(),
    }), 201


@users_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required_role("admin")
@limiter.limit("10/minute")
def update_user(user_id):
    """Update an existing user."""
    user = User.query.get_or_404(user_id)
    data = request.json or {}

    if "username" in data:
        existing = User.query.filter_by(username=data["username"]).first()
        if existing and existing.id != user_id:
            return jsonify({"status": "error", "message": "Username already exists"}), 409
        user.username = data["username"]

    if "email" in data:
        existing = User.query.filter_by(email=data["email"]).first()
        if existing and existing.id != user_id:
            return jsonify({"status": "error", "message": "Email already exists"}), 409
        user.email = data["email"]

    if "first_name" in data:
        user.first_name = data["first_name"]
    if "last_name" in data:
        user.last_name = data["last_name"]
    if "role" in data:
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "password" in data and data["password"]:
        user.password_hash = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "User updated successfully",
        "data": user.to_dict(),
    })


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required_role("admin")
@limiter.limit("5/minute")
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "User deleted successfully",
        "data": { "id": user_id },
    })