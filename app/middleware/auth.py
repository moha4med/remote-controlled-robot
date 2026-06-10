# app/middleware/auth.py
# Custom authentication middleware for Flask routes, providing JWT verification and role-based access control.

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.models.user import User


def jwt_required_v1():
    """
    Protect all /api/v1 routes — verifies JWT only, no role check.
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 401

            return fn(*args, **kwargs)
        return decorator
    return wrapper


def jwt_required_role(required_role=None):
    """
    Protect routes that require a specific role.
    Verifies JWT and checks the user's role against the required role.
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            user = User.query.get(user_id)
            if not user:
                return jsonify({
                    "status": "error",
                    "message": "User not found"
                }), 401

            if not user.is_active:
                return jsonify({
                    "status": "error",
                    "message": "Account is deactivated"
                }), 403

            if required_role and user.role != required_role:
                return jsonify({
                    "status": "error",
                    "message": f"Insufficient permissions. Required role: {required_role}"
                }), 403

            return fn(*args, **kwargs)
        return decorator
    return wrapper