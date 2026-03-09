import csv
from io import StringIO
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from flask_login import login_required, current_user
from extensions import db
from models import User, DoctorProfile, PatientProfile, Assignment
from .utils import role_required, save_diagnosis_images, delete_diagnosis_images
from services.notifier import notify_doctor_patient_assigned


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", methods=["GET", "POST"])
@login_required
@role_required("admin")
def dashboard():
    q = request.args.get("q", "").strip()
    role_filter = request.args.get("role", "all")

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "doctor":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            full_name = request.form.get("full_name", "").strip()
            doctor_id = request.form.get("doctor_id", "").strip()
            department = request.form.get("department", "").strip()

            if not all([username, email, password, full_name, doctor_id, department]):
                flash("All doctor fields are required.", "error")
            elif (
                User.query.filter_by(username=username).first()
                or User.query.filter_by(email=email).first()
                or DoctorProfile.query.filter_by(doctor_id=doctor_id).first()
            ):
                flash("Doctor username, email, or doctor ID already exists.", "error")
            else:
                user = User(
                    username=username,
                    email=email,
                    password_hash=User.hash_password(password),
                    role="doctor",
                    full_name=full_name,
                )
                db.session.add(user)
                db.session.flush()
                profile = DoctorProfile(user_id=user.id, doctor_id=doctor_id, department=department)
                db.session.add(profile)
                db.session.commit()
                flash("Doctor created.", "success")

        if form_type == "patient":
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
            elif (
                User.query.filter_by(username=username).first()
                or User.query.filter_by(email=email).first()
                or PatientProfile.query.filter_by(patient_id=patient_id).first()
            ):
                flash("Patient username, email, or patient ID already exists.", "error")
            else:
                user = User(
                    username=username,
                    email=email,
                    password_hash=User.hash_password(password),
                    role="patient",
                    full_name=full_name,
                )
                db.session.add(user)
                db.session.flush()
                profile = PatientProfile(
                    user_id=user.id,
                    patient_id=patient_id,
                    age=int(age),
                    gender=gender,
                    phone=phone or None,
                    address=address or None,
                    diagnosis=diagnosis or None,
                    doctor_notes=doctor_notes or None,
                )
                profile.set_diagnosis_images(diagnosis_images)
                db.session.add(profile)
                db.session.commit()
                flash("Patient created.", "success")

        if form_type == "assign":
            doctor_id = request.form.get("doctor_id", "").strip()
            patient_id = request.form.get("patient_id", "").strip()
            doctor = DoctorProfile.query.filter_by(doctor_id=doctor_id).first()
            patient = PatientProfile.query.filter_by(patient_id=patient_id).first()
            if not doctor or not patient:
                flash("Doctor ID or Patient ID not found.", "error")
            else:
                existing = Assignment.query.filter_by(doctor_id=doctor.id, patient_id=patient.id).first()
                if existing:
                    flash("Assignment already exists.", "error")
                else:
                    db.session.add(Assignment(doctor_id=doctor.id, patient_id=patient.id))
                    db.session.commit()
                    flash("Patient assigned to doctor.", "success")

    doctor_query = DoctorProfile.query
    patient_query = PatientProfile.query
    assignment_query = Assignment.query

    if q:
        doctor_query = doctor_query.join(User).filter(
            (DoctorProfile.doctor_id.ilike(f"%{q}%")) |
            (DoctorProfile.department.ilike(f"%{q}%")) |
            (User.full_name.ilike(f"%{q}%")) |
            (User.email.ilike(f"%{q}%")) |
            (User.username.ilike(f"%{q}%"))
        )
        patient_query = patient_query.join(User).filter(
            (PatientProfile.patient_id.ilike(f"%{q}%")) |
            (PatientProfile.diagnosis.ilike(f"%{q}%")) |
            (User.full_name.ilike(f"%{q}%")) |
            (User.email.ilike(f"%{q}%")) |
            (User.username.ilike(f"%{q}%"))
        )
        assignment_query = assignment_query.join(DoctorProfile).join(PatientProfile).filter(
            (DoctorProfile.doctor_id.ilike(f"%{q}%")) |
            (PatientProfile.patient_id.ilike(f"%{q}%"))
        )

    if role_filter == "doctors":
        patients = []
        assignments = []
        doctors = doctor_query.all()
    elif role_filter == "patients":
        doctors = []
        assignments = []
        patients = patient_query.all()
    elif role_filter == "assignments":
        doctors = []
        patients = []
        assignments = assignment_query.all()
    else:
        doctors = doctor_query.all()
        patients = patient_query.all()
        assignments = assignment_query.all()

    return render_template(
        "admin_dashboard.html",
        doctors=doctors,
        patients=patients,
        assignments=assignments,
        q=q,
        role_filter=role_filter,
    )


@admin_bp.route("/admin/doctors/<int:doctor_profile_id>/patients")
@login_required
@role_required("admin")
def doctor_patients(doctor_profile_id):
    doctor = DoctorProfile.query.get_or_404(doctor_profile_id)
    assignments = (
        Assignment.query
        .filter_by(doctor_id=doctor.id)
        .join(PatientProfile)
        .join(User, PatientProfile.user_id == User.id)
        .order_by(PatientProfile.patient_id.asc())
        .all()
    )
    return render_template(
        "admin_doctor_patients.html",
        doctor=doctor,
        assignments=assignments,
    )


@admin_bp.route("/admin/doctors/<int:doctor_profile_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_doctor(doctor_profile_id):
    profile = DoctorProfile.query.get_or_404(doctor_profile_id)
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        full_name = request.form.get("full_name", "").strip()
        doctor_id = request.form.get("doctor_id", "").strip()
        department = request.form.get("department", "").strip()

        if not all([username, email, full_name, doctor_id, department]):
            flash("All fields except password are required.", "error")
            return redirect(url_for("admin.edit_doctor", doctor_profile_id=doctor_profile_id))

        existing_user = User.query.filter(User.username == username, User.id != profile.user_id).first()
        existing_email = User.query.filter(User.email == email, User.id != profile.user_id).first()
        existing_doctor_id = DoctorProfile.query.filter(
            DoctorProfile.doctor_id == doctor_id,
            DoctorProfile.id != profile.id
        ).first()
        if existing_user or existing_email or existing_doctor_id:
            flash("Username, email, or Doctor ID already exists.", "error")
            return redirect(url_for("admin.edit_doctor", doctor_profile_id=doctor_profile_id))

        profile.user.username = username
        profile.user.email = email
        if password:
            profile.user.password_hash = User.hash_password(password)
        profile.user.full_name = full_name
        profile.doctor_id = doctor_id
        profile.department = department
        db.session.commit()
        flash("Doctor updated.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin_doctor_edit.html", profile=profile)


@admin_bp.route("/admin/doctors/<int:doctor_profile_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_doctor(doctor_profile_id):
    profile = DoctorProfile.query.get_or_404(doctor_profile_id)
    db.session.delete(profile)
    db.session.delete(profile.user)
    db.session.commit()
    flash("Doctor deleted.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/patients/<int:patient_profile_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_patient(patient_profile_id):
    profile = PatientProfile.query.get_or_404(patient_profile_id)
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        full_name = request.form.get("full_name", "").strip()
        patient_id = request.form.get("patient_id", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        diagnosis = request.form.get("diagnosis", "").strip()
        doctor_notes = request.form.get("doctor_notes", "").strip()
        new_images = save_diagnosis_images(request.files.getlist("diagnosis_images"))
        removed_images = request.form.getlist("remove_diagnosis_images")

        if not all([username, email, full_name, patient_id, age, gender]):
            flash("All fields except password/phone/address/notes are required.", "error")
            return redirect(url_for("admin.edit_patient", patient_profile_id=patient_profile_id))

        existing_user = User.query.filter(User.username == username, User.id != profile.user_id).first()
        existing_email = User.query.filter(User.email == email, User.id != profile.user_id).first()
        existing_patient_id = PatientProfile.query.filter(
            PatientProfile.patient_id == patient_id,
            PatientProfile.id != profile.id
        ).first()
        if existing_user or existing_email or existing_patient_id:
            flash("Username, email, or Patient ID already exists.", "error")
            return redirect(url_for("admin.edit_patient", patient_profile_id=patient_profile_id))

        profile.user.username = username
        profile.user.email = email
        if password:
            profile.user.password_hash = User.hash_password(password)
        profile.user.full_name = full_name
        profile.patient_id = patient_id
        profile.age = int(age)
        profile.gender = gender
        profile.phone = phone or None
        profile.address = address or None
        profile.diagnosis = diagnosis or None
        remaining_images = [img for img in profile.diagnosis_image_list if img not in removed_images]
        profile.set_diagnosis_images(remaining_images + new_images)
        delete_diagnosis_images(removed_images)
        profile.doctor_notes = doctor_notes or None
        db.session.commit()
        flash("Patient updated.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin_patient_edit.html", profile=profile)


@admin_bp.route("/admin/patients/<int:patient_profile_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_patient(patient_profile_id):
    profile = PatientProfile.query.get_or_404(patient_profile_id)
    db.session.delete(profile)
    db.session.delete(profile.user)
    db.session.commit()
    flash("Patient deleted.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/assignments/<int:assignment_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if request.method == "POST":
        doctor_id = request.form.get("doctor_id", "").strip()
        patient_id = request.form.get("patient_id", "").strip()
        doctor = DoctorProfile.query.filter_by(doctor_id=doctor_id).first()
        patient = PatientProfile.query.filter_by(patient_id=patient_id).first()
        if not doctor or not patient:
            flash("Doctor ID or Patient ID not found.", "error")
            return redirect(url_for("admin.edit_assignment", assignment_id=assignment_id))
        existing = Assignment.query.filter_by(doctor_id=doctor.id, patient_id=patient.id).first()
        if existing and existing.id != assignment.id:
            flash("Assignment already exists.", "error")
            return redirect(url_for("admin.edit_assignment", assignment_id=assignment_id))

        assignment.doctor_id = doctor.id
        assignment.patient_id = patient.id
        db.session.commit()
        flash("Assignment updated.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin_assignment_edit.html", assignment=assignment)


@admin_bp.route("/admin/assignments/<int:assignment_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    db.session.delete(assignment)
    db.session.commit()
    flash("Assignment deleted.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/assignments/<int:assignment_id>/notify", methods=["POST"])
@login_required
@role_required("admin")
def notify_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    notify_doctor_patient_assigned(
        assignment.doctor.user,
        assignment.patient,
        assigned_by=current_user.username,
    )
    flash("Notification logged: assignment email sent to doctor.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/export/doctors")
@login_required
@role_required("admin")
def export_doctors():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Doctor ID", "Name", "Username", "Email", "Department"])
    for d in DoctorProfile.query.join(User).all():
        writer.writerow([d.doctor_id, d.user.full_name, d.user.username, d.user.email, d.department])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=doctors.csv"})


@admin_bp.route("/admin/export/patients")
@login_required
@role_required("admin")
def export_patients():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Patient ID", "Name", "Username", "Email", "Age", "Gender", "Phone", "Address", "Diagnosis", "Diagnosis Images", "Notes"])
    for p in PatientProfile.query.join(User).all():
        writer.writerow([
            p.patient_id, p.user.full_name, p.user.username, p.user.email,
            p.age, p.gender, p.phone, p.address, p.diagnosis, "; ".join(p.diagnosis_image_list), p.doctor_notes
        ])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=patients.csv"})


@admin_bp.route("/admin/export/assignments")
@login_required
@role_required("admin")
def export_assignments():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Doctor ID", "Patient ID"])
    for a in Assignment.query.all():
        writer.writerow([a.doctor.doctor_id, a.patient.patient_id])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=assignments.csv"})
