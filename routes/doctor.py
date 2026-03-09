from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import db
from models import User, PatientProfile, Assignment, PatientHistory
from .utils import role_required, is_assigned_to_doctor, save_diagnosis_images, delete_diagnosis_images
from services.notifier import notify_doctor_new_image_added


doctor_bp = Blueprint("doctor", __name__)


@doctor_bp.route("/doctor")
@login_required
@role_required("doctor")
def dashboard():
    profile = current_user.doctor_profile
    q = request.args.get("q", "").strip()
    if profile:
        query = Assignment.query.filter_by(doctor_id=profile.id)
        if q:
            query = query.join(PatientProfile).join(User).filter(
                (PatientProfile.patient_id.ilike(f"%{q}%")) |
                (PatientProfile.diagnosis.ilike(f"%{q}%")) |
                (User.full_name.ilike(f"%{q}%")) |
                (User.email.ilike(f"%{q}%")) |
                (User.username.ilike(f"%{q}%"))
            )
        assignments = query.all()
    else:
        assignments = []
    return render_template("doctor_dashboard.html", profile=profile, assignments=assignments, q=q)


@doctor_bp.route("/doctor/patients/new", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def create_patient():
    profile = current_user.doctor_profile
    if not profile:
        flash("No doctor profile found.", "error")
        return redirect(url_for("doctor.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        patient_id = request.form.get("patient_id", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        diagnosis = request.form.get("diagnosis", "").strip()
        doctor_notes = request.form.get("doctor_notes", "").strip()
        diagnosis_images = save_diagnosis_images(request.files.getlist("diagnosis_images"))

        if not all([username, email, password, full_name, patient_id, age, gender]):
            flash("All patient fields are required.", "error")
            return redirect(url_for("doctor.create_patient"))
        if (
            User.query.filter_by(username=username).first()
            or User.query.filter_by(email=email).first()
            or PatientProfile.query.filter_by(patient_id=patient_id).first()
        ):
            flash("Patient username, email, or patient ID already exists.", "error")
            return redirect(url_for("doctor.create_patient"))

        user = User(
            username=username,
            email=email,
            password_hash=User.hash_password(password),
            role="patient",
            full_name=full_name,
        )
        db.session.add(user)
        db.session.flush()
        patient = PatientProfile(
            user_id=user.id,
            patient_id=patient_id,
            age=int(age),
            gender=gender,
            phone=phone or None,
            address=address or None,
            diagnosis=diagnosis or None,
            doctor_notes=doctor_notes or None,
        )
        patient.set_diagnosis_images(diagnosis_images)
        db.session.add(patient)
        db.session.flush()
        db.session.add(Assignment(doctor_id=profile.id, patient_id=patient.id))
        db.session.commit()
        flash("Patient created and assigned.", "success")
        return redirect(url_for("doctor.dashboard"))

    return render_template("doctor_patient_new.html")


@doctor_bp.route("/doctor/patients/<int:patient_profile_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def edit_patient(patient_profile_id):
    profile = current_user.doctor_profile
    patient = PatientProfile.query.get_or_404(patient_profile_id)
    if not is_assigned_to_doctor(profile, patient):
        flash("You are not assigned to this patient.", "error")
        return redirect(url_for("doctor.dashboard"))

    history_entries = PatientHistory.query.filter_by(patient_id=patient.id).order_by(PatientHistory.created_at.desc()).all()

    if request.method == "POST":
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        diagnosis = request.form.get("diagnosis", "").strip()
        doctor_notes = request.form.get("doctor_notes", "").strip()
        history_note = request.form.get("history_note", "").strip()
        new_images = save_diagnosis_images(request.files.getlist("diagnosis_images"))
        removed_images = request.form.getlist("remove_diagnosis_images")

        if not all([age, gender]):
            flash("Age and gender are required.", "error")
            return redirect(url_for("doctor.edit_patient", patient_profile_id=patient_profile_id))

        patient.age = int(age)
        patient.gender = gender
        patient.phone = phone or None
        patient.address = address or None
        patient.diagnosis = diagnosis or None
        remaining_images = [img for img in patient.diagnosis_image_list if img not in removed_images]
        patient.set_diagnosis_images(remaining_images + new_images)
        delete_diagnosis_images(removed_images)
        patient.doctor_notes = doctor_notes or None
        if history_note:
            db.session.add(PatientHistory(
                patient_id=patient.id,
                doctor_id=profile.id,
                note=history_note,
            ))
        db.session.commit()
        flash("Patient details updated.", "success")
        return redirect(url_for("doctor.dashboard"))

    return render_template("doctor_patient_edit.html", patient=patient, history_entries=history_entries)


@doctor_bp.route("/doctor/patients/<int:patient_profile_id>/notify-new-image", methods=["POST"])
@login_required
@role_required("doctor")
def notify_new_image(patient_profile_id):
    profile = current_user.doctor_profile
    patient = PatientProfile.query.get_or_404(patient_profile_id)
    if not is_assigned_to_doctor(profile, patient):
        flash("You are not assigned to this patient.", "error")
        return redirect(url_for("doctor.dashboard"))

    notify_doctor_new_image_added(
        profile.user,
        patient,
        notified_by=current_user.username,
    )
    flash("Notification logged: new-image email sent to doctor.", "success")
    return redirect(url_for("doctor.edit_patient", patient_profile_id=patient_profile_id))
