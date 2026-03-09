import os
import uuid
from functools import wraps
from flask import flash, redirect, url_for, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from models import Assignment


def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role != role:
                flash("Access denied.", "error")
                return redirect(url_for("auth.index"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def is_assigned_to_doctor(doctor_profile, patient_profile):
    if not doctor_profile or not patient_profile:
        return False
    return Assignment.query.filter_by(
        doctor_id=doctor_profile.id,
        patient_id=patient_profile.id,
    ).first() is not None


def save_diagnosis_images(files):
    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
    saved_paths = []
    upload_dir = os.path.join(current_app.static_folder, "uploads", "diagnosis")
    os.makedirs(upload_dir, exist_ok=True)

    for file in files:
        if not file or not file.filename:
            continue
        filename = secure_filename(file.filename)
        if "." not in filename:
            continue
        ext = filename.rsplit(".", 1)[1].lower()
        if ext not in allowed_extensions:
            continue
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(upload_dir, unique_name))
        saved_paths.append(f"uploads/diagnosis/{unique_name}")

    return saved_paths


def delete_diagnosis_images(image_paths):
    upload_root = os.path.join("uploads", "diagnosis")
    for image_path in image_paths:
        normalized = os.path.normpath(image_path).replace("\\", "/")
        if not normalized.startswith(upload_root):
            continue
        file_path = os.path.join(current_app.static_folder, normalized)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
