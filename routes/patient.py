from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Assignment
from .utils import role_required


patient_bp = Blueprint("patient", __name__)


@patient_bp.route("/patient")
@login_required
@role_required("patient")
def dashboard():
    profile = current_user.patient_profile
    assigned = Assignment.query.filter_by(patient_id=profile.id).all() if profile else []
    return render_template("patient_dashboard.html", profile=profile, assignments=assigned)
