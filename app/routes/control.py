from flask import Blueprint, render_template


control_bp = Blueprint("control", __name__)


@control_bp.route("/control")
def index():
    return render_template("control.html")
