from flask import Blueprint, render_template


sensors_page_bp = Blueprint("sensors", __name__)


@sensors_page_bp.route("/sensors")
def index():
    return render_template("sensors.html")
