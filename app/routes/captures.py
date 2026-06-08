# app/routes/captures.py
# HTML page route for the captures gallery.

from flask import Blueprint, render_template

captures_page_bp = Blueprint("captures", __name__)


@captures_page_bp.route("/captures")
def index():
    return render_template("captures.html")