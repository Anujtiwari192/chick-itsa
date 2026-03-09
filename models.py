import json
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, doctor, patient
    full_name = db.Column(db.String(120), nullable=False)

    doctor_profile = db.relationship("DoctorProfile", backref="user", uselist=False)
    patient_profile = db.relationship("PatientProfile", backref="user", uselist=False)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)


class DoctorProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    doctor_id = db.Column(db.String(50), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)

    assignments = db.relationship("Assignment", backref="doctor", cascade="all, delete-orphan")


class PatientProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    patient_id = db.Column(db.String(50), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    diagnosis = db.Column(db.Text, nullable=True)
    diagnosis_images = db.Column(db.Text, nullable=True)
    doctor_notes = db.Column(db.Text, nullable=True)

    assignments = db.relationship("Assignment", backref="patient", cascade="all, delete-orphan")

    @property
    def diagnosis_image_list(self):
        if not self.diagnosis_images:
            return []
        try:
            data = json.loads(self.diagnosis_images)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def set_diagnosis_images(self, image_paths):
        self.diagnosis_images = json.dumps(image_paths or [])


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor_profile.id"), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient_profile.id"), nullable=False)


class PatientHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient_profile.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor_profile.id"), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    patient = db.relationship("PatientProfile", backref="history_entries")
    doctor = db.relationship("DoctorProfile", backref="history_entries")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
