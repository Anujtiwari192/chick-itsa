from datetime import datetime


def _log_email(to_email, subject, body):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print("[NOTIFIER] Simulated email sent")
    print(f"[NOTIFIER] Time: {timestamp}")
    print(f"[NOTIFIER] To: {to_email}")
    print(f"[NOTIFIER] Subject: {subject}")
    print(f"[NOTIFIER] Body: {body}")


def notify_doctor_patient_assigned(doctor_user, patient_profile, assigned_by):
    subject = f"New Patient Assigned: {patient_profile.patient_id}"
    body = (
        f"Hello {doctor_user.full_name}, patient "
        f"{patient_profile.user.full_name} ({patient_profile.patient_id}) "
        f"has been assigned to you by {assigned_by}."
    )
    _log_email(doctor_user.email, subject, body)


def notify_doctor_new_image_added(doctor_user, patient_profile, notified_by):
    image_count = len(patient_profile.diagnosis_image_list)
    subject = f"New Image Added: {patient_profile.patient_id}"
    body = (
        f"Hello {doctor_user.full_name}, new diagnosis image(s) were added for "
        f"{patient_profile.user.full_name} ({patient_profile.patient_id}). "
        f"Current image count: {image_count}. Triggered by {notified_by}."
    )
    _log_email(doctor_user.email, subject, body)
