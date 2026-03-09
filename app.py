import os
from sqlalchemy import text
from flask import Flask
from extensions import db, login_manager
from models import User, DoctorProfile, PatientProfile, Assignment
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.doctor import doctor_bp
from routes.patient import patient_bp

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")

HOST = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
PORT = int(os.environ.get("FLASK_RUN_PORT", "5000"))
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"


def create_app(testing=False, db_path=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    if db_path is None:
        db_path = DB_PATH
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if testing:
        app.config["TESTING"] = True

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patient_bp)

    return app


app = create_app()


def ensure_user_email_column():
    # Backfill path for existing sqlite DBs created before email existed.
    columns = db.session.execute(text("PRAGMA table_info(user)")).all()
    has_email = any(row[1] == "email" for row in columns)
    if not has_email:
        db.session.execute(text("ALTER TABLE user ADD COLUMN email VARCHAR(120)"))
    db.session.execute(text("UPDATE user SET email = lower(username || '@local.app') WHERE email IS NULL OR email = ''"))
    db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_email ON user (email)"))
    db.session.commit()


def seed_doctors():
    mock_doctors = [
        ("dr.richa", "dr.richa@medanta", "Dr. Richa Tiwari", "Paediatrics", "PED-001"),
        ("dr.aarti", "dr.aarti@medanta", "Dr. Aarti Mehra", "Paediatrics", "PED-002"),
        ("dr.kunal", "dr.kunal@medanta", "Dr. Kunal Sharma", "Paediatrics", "PED-003"),
        ("dr.bhanu", "dr.bhanu@medanta", "Dr. Bhanu", "Orthopaedics", "ORT-001"),
        ("dr.nikhil", "dr.nikhil@medanta", "Dr. Nikhil Rao", "Orthopaedics", "ORT-002"),
        ("dr.megha", "dr.megha@medanta", "Dr. Megha Sinha", "Orthopaedics", "ORT-003"),
        ("dr.agraj", "dr.agraj@medanta", "Dr. Agraj Tiwari", "Opthalmology", "OPT-001"),
        ("dr.arun", "dr.arun@medanta", "Dr. Arun Patel", "Opthalmology", "OPT-002"),
        ("dr.sana", "dr.sana@medanta", "Dr. Sana Ali", "Opthalmology", "OPT-003"),
    ]

    created = 0
    for username, email, full_name, department, doctor_id in mock_doctors:
        existing_user = User.query.filter_by(username=username).first()
        existing_profile = DoctorProfile.query.filter_by(doctor_id=doctor_id).first()
        if existing_user or existing_profile:
            continue

        user = User(
            username=username,
            email=email,
            password_hash=User.hash_password("baingan"),
            role="doctor",
            full_name=full_name,
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(
            DoctorProfile(
                user_id=user.id,
                doctor_id=doctor_id,
                department=department,
            )
        )
        created += 1

    if created:
        db.session.commit()
    return created


def seed_patients_and_assignments():
    mock_patients = [
        # Paediatrics-heavy
        ("patient.aarav", "patient.aarav@medanta", "Aarav Sharma", "PAT-001", 8, "Male", "9876500001", "Indore", "Viral fever", "Hydration advised"),
        ("patient.anaya", "patient.anaya@medanta", "Anaya Verma", "PAT-002", 6, "Female", "9876500002", "Bhopal", "Seasonal flu", "Review in 3 days"),
        # Orthopaedics-heavy
        ("patient.anuj", "patient.anuj@medanta", "Anuj Tiwari", "PAT-003", 39, "Male", "9876500003", "Gwalior", "Knee pain", "Physio recommended"),
        ("patient.kavya", "patient.kavya@medanta", "Kavya Singh", "PAT-004", 31, "Female", "9876500004", "Dewas", "Back strain", "Rest and analgesics"),
        # Opthalmology-heavy
        ("patient.neha", "patient.neha@medanta", "Neha Tandon", "PAT-005", 27, "Female", "9876500005", "Gwalior", "Dry eye", "Lubricating drops"),
        ("patient.rohan", "patient.rohan@medanta", "Rohan Patel", "PAT-006", 45, "Male", "9876500006", "Ratlam", "Blurred vision", "Refraction advised"),
        # Common across departments
        ("patient.anujt", "patient.anujt@medanta", "Anujtiw", "PAT-007", 7, "Male", "9876500007", "Jabalpur", "Headache and eye strain", "Multi-dept follow-up"),
        ("patient.imran", "patient.imran@medanta", "Imran Khan", "PAT-008", 52, "Male", "9876500008", "Sagar", "Diabetes-related concerns", "Cross-specialty monitoring"),
    ]

    patient_assignments = {
        "patient.aarav": ["dr.richa"],
        "patient.anaya": ["dr.aarti"],
        "patient.anuj": ["dr.bhanu"],
        "patient.kavya": ["dr.nikhil"],
        "patient.neha": ["dr.agraj"],
        "patient.rohan": ["dr.arun"],
        "patient.anujt": ["dr.richa", "dr.bhanu", "dr.agraj"],
        "patient.imran": ["dr.kunal", "dr.megha", "dr.arun"],
    }

    doctor_by_username = {
        d.user.username: d for d in DoctorProfile.query.join(User).all()
    }

    created_patients = 0
    created_assignments = 0

    for username, email, full_name, patient_id, age, gender, phone, address, diagnosis, notes in mock_patients:
        user = User.query.filter_by(username=username).first()
        patient = PatientProfile.query.filter_by(patient_id=patient_id).first()

        if not patient:
            if not user:
                user = User(
                    username=username,
                    email=email,
                    password_hash=User.hash_password("baingan"),
                    role="patient",
                    full_name=full_name,
                )
                db.session.add(user)
                db.session.flush()
            elif user.role != "patient":
                continue

            patient = user.patient_profile
            if not patient:
                patient = PatientProfile(
                    user_id=user.id,
                    patient_id=patient_id,
                    age=age,
                    gender=gender,
                    phone=phone,
                    address=address,
                    diagnosis=diagnosis,
                    doctor_notes=notes,
                )
                db.session.add(patient)
                db.session.flush()
                created_patients += 1

        for doctor_username in patient_assignments.get(username, []):
            doctor = doctor_by_username.get(doctor_username)
            if not doctor:
                continue
            existing_assignment = Assignment.query.filter_by(
                doctor_id=doctor.id,
                patient_id=patient.id,
            ).first()
            if existing_assignment:
                continue
            db.session.add(Assignment(doctor_id=doctor.id, patient_id=patient.id))
            created_assignments += 1

    if created_patients or created_assignments:
        db.session.commit()

    return created_patients, created_assignments


@app.cli.command("initdb")
def initdb():
    with app.app_context():
        db.create_all()
        ensure_user_email_column()
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@medanta",
                password_hash=User.hash_password("admin123"),
                role="admin",
                full_name="Administrator",
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin / admin123")
        else:
            if not admin.email:
                admin.email = "admin@medanta"
                db.session.commit()
            print("Admin already exists.")

        seeded_count = seed_doctors()
        if seeded_count:
            print(f"Seeded {seeded_count} mock doctors (password: baingan)")
        else:
            print("Mock doctors already exist.")

        patient_count, assignment_count = seed_patients_and_assignments()
        if patient_count or assignment_count:
            print(
                f"Seeded {patient_count} mock patients and {assignment_count} assignments "
                "(patient password: baingan)"
            )
        else:
            print("Mock patients and assignments already exist.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_user_email_column()
    app.run(host=HOST, port=PORT, debug=DEBUG)
