# app/routes/api/v1/crops.py
# API routes for crop management

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db, limiter
from app.models.crop_profile import CropProfile
from app.models.user import User

crops_bp = Blueprint("crops", __name__, url_prefix="/api/v1/crops")


@crops_bp.route("/", methods=["GET"])
@jwt_required()
@limiter.limit("30/minute")
def list_crops():
    """List all active crop profiles."""
    crops = CropProfile.query.filter_by(is_active=True).all()
    return jsonify({"status": "success", "data": [c.to_dict() for c in crops]})


@crops_bp.route("/", methods=["POST"])
@jwt_required()
@limiter.limit("10/minute")
def create_crop():
    """Create a new crop profile."""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    if user.role != "admin":
        return jsonify({"status": "error", "message": "Admin access required"}), 403
    
    data = request.json or {}
    required_fields = ["name", "optimal_temp_min", "optimal_temp_max","optimal_humidity_min", "optimal_humidity_max"]
    
    for field in required_fields:
        if field not in data:
            return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
        
    if data["optimal_temp_min"] >= data["optimal_temp_max"]:
        return jsonify({"status": "error", "message": "optimal_temp_min must be less than optimal_temp_max"}), 400

    if data["optimal_humidity_min"] >= data["optimal_humidity_max"]:
        return jsonify({"status": "error", "message": "optimal_humidity_min must be less than optimal_humidity_max"}), 400

    crop = CropProfile(
        name=data["name"],
        optimal_temp_min=float(data["optimal_temp_min"]),
        optimal_temp_max=float(data["optimal_temp_max"]),
        optimal_humidity_min=float(data["optimal_humidity_min"]),
        optimal_humidity_max=float(data["optimal_humidity_max"]),
        frost_sensitive=data.get("frost_sensitive", True),
        description=data.get("description", "")
    )

    db.session.add(crop)
    db.session.commit()

    return jsonify({"status": "success", "data": crop.to_dict()}), 201


@crops_bp.route("/<int:crop_id>", methods=["PUT"])
@jwt_required()
@limiter.limit("10/minute")
def update_crop(crop_id):
    """Update an existing crop profile. Admin only."""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    if user.role != "admin":
        return jsonify({"status": "error", "message": "Admin access required"}), 403
    
    crop = CropProfile.query.get_or_404(crop_id)
    data = request.json or {}
    
    for field in ["name", "optimal_temp_min", "optimal_temp_max","optimal_humidity_min", "optimal_humidity_max", "frost_sensitive", "description"]:
        if field in data:
            setattr(crop, field, data[field])
            
    db.session.commit()
    
    return jsonify({"status": "success", "data": crop.to_dict()})


@crops_bp.route("/<int:crop_id>", methods=["DELETE"])
@jwt_required()
@limiter.limit("10/minute")
def delete_crop(crop_id):
    """Soft-delete a crop profile (set is_active=False). Admin only."""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    if user.role != "admin":
        return jsonify({"status": "error", "message": "Admin access required"}), 403
    
    crop = CropProfile.query.get_or_404(crop_id)
    crop.is_active = False
    db.session.commit()
    
    return jsonify({"status": "success", "message": f"Crop '{crop.name}' deactivated."})


@crops_bp.route("/active", methods=["PUT"])
@jwt_required()
@limiter.limit("10/minute")
def set_active_crop():
    """Set the active crops for the current user. Accespts a list of crops IDs. Any authenticated user."""
    user_id = int(get_jwt_identity())
    data = request.json or {}
    crop_ids = data.get("crop_ids", [])
    
    # Validate crop IDs and ensure they are active
    crops = []
    for crop_id in crop_ids:
        crop = CropProfile.query.get(crop_id)
        if not crop or not crop.is_active:
            return jsonify({"status": "error", "message": f"Crop with ID {crop_id} not found or inactive"}), 400
        crops.append(crop)
        
    # Store the list of crop IDs as JSON in the user's settings
    from app.models.setting import Setting
    Setting.set_user_preference(user_id, "active_crop_ids", [crop.id for crop in crops])
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "message": f"Active crops set to '{[crop.name for crop in crops]}'." if crops else "Active crops cleared.",
        "data": [crop.to_dict() for crop in crops] if crops else None,
    })