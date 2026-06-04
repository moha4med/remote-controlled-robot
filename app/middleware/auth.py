from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

def jwt_required_v1():
    """
    Protect all /api/v1 routes
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 401
                
            return fn(user_id, *args, **kwargs)
        return decorator
    return wrapper

def jwt_required_role(required_role=None):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            # later you fetch user from DB
            # user.role check

            return fn(user_id, *args, **kwargs)
        return decorator
    return wrapper
