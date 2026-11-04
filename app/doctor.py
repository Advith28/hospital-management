"""
Doctor portal for MediFlow:
- Doctor clinical dashboard with today's appointments and calendar
- Consultation completion, diagnosis notes, and prescription entry
- Schedule & availability settings update
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import datetime
from app.database import get_db_connection
from app.auth import login_required

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

@doctor_bp.route('/dashboard')
@login_required(role='doctor')
def dashboard():
    """Doctor dashboard showing patient schedule, statistics, and quick consultation actions."""
    conn = get_db_connection()
    user_id = session['user_id']
    
    doctor = conn.execute("""
        SELECT d.*, dept.name as department_name, u.full_name, u.email, u.phone
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        JOIN departments dept ON d.department_id = dept.id
        WHERE d.user_id = ?
    """, (user_id,)).fetchone()

    if not doctor:
        conn.close()
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('auth.logout'))

    doctor_id = doctor['id']
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    # All appointments for doctor
    appointments = conn.execute("""
        SELECT a.*, u.full_name as patient_name, u.phone as patient_phone, u.email as patient_email,
               p.gender, p.blood_group, p.dob
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users u ON p.user_id = u.id
        WHERE a.doctor_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time ASC
    """, (doctor_id,)).fetchall()

    today_appointments = [a for a in appointments if a['appointment_date'] == today_str]
    upcoming_count = sum(1 for a in appointments if a['appointment_date'] >= today_str and a['status'] in ('Scheduled', 'Rescheduled'))
    completed_count = sum(1 for a in appointments if a['status'] == 'Completed')
    total_patients_seen = len(set(a['patient_id'] for a in appointments if a['status'] == 'Completed'))

    conn.close()

    return render_template('doctor/dashboard.html',
                           doctor=doctor,
                           appointments=appointments,
                           today_appointments=today_appointments,
                           today_str=today_str,
                           upcoming_count=upcoming_count,
                           completed_count=completed_count,
                           total_patients_seen=total_patients_seen)

@doctor_bp.route('/consult/<int:appointment_id>', methods=['GET', 'POST'])
@login_required(role='doctor')
def consult(appointment_id):
    """Conduct or record clinical notes and electronic prescription for an appointment."""
    conn = get_db_connection()
    user_id = session['user_id']
    doctor = conn.execute("SELECT id FROM doctors WHERE user_id = ?", (user_id,)).fetchone()

    appt = conn.execute("""
        SELECT a.*, u.full_name as patient_name, u.phone as patient_phone, u.email as patient_email,
               p.gender, p.blood_group, p.dob, p.address, p.emergency_contact
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users u ON p.user_id = u.id
        WHERE a.id = ? AND a.doctor_id = ?
    """, (appointment_id, doctor['id'])).fetchone()

    if not appt:
        conn.close()
        flash('Appointment record not found or unauthorized access.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    if request.method == 'POST':
        doctor_notes = request.form.get('doctor_notes', '').strip()
        prescription = request.form.get('prescription', '').strip()
        status = request.form.get('status', 'Completed')

        conn.execute("""
            UPDATE appointments
            SET doctor_notes = ?, prescription = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (doctor_notes, prescription, status, appointment_id))
        conn.commit()
        conn.close()

        flash(f'Clinical consultation notes for {appt["patient_name"]} updated successfully.', 'success')
        return redirect(url_for('doctor.dashboard'))

    # Previous consultations for this patient
    history = conn.execute("""
        SELECT a.*, d.specialization, u.full_name as doctor_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN users u ON d.user_id = u.id
        WHERE a.patient_id = ? AND a.id != ?
        ORDER BY a.appointment_date DESC
    """, (appt['patient_id'], appointment_id)).fetchall()

    conn.close()
    return render_template('doctor/consult.html', appt=appt, history=history)

@doctor_bp.route('/schedule', methods=['GET', 'POST'])
@login_required(role='doctor')
def schedule():
    """Configure working days, consultation timing, fee, and bio."""
    conn = get_db_connection()
    user_id = session['user_id']

    if request.method == 'POST':
        specialization = request.form.get('specialization', '').strip()
        qualification = request.form.get('qualification', '').strip()
        experience_years = request.form.get('experience_years', type=int) or 1
        consultation_fee = request.form.get('consultation_fee', type=float) or 500.0
        available_days = request.form.getlist('days')
        slot_start_time = request.form.get('slot_start_time', '09:00')
        slot_end_time = request.form.get('slot_end_time', '17:00')
        slot_duration_mins = request.form.get('slot_duration_mins', type=int) or 30
        bio = request.form.get('bio', '').strip()

        days_joined = ", ".join(available_days) if available_days else "Monday, Tuesday, Wednesday, Thursday, Friday"

        conn.execute("""
            UPDATE doctors
            SET specialization = ?, qualification = ?, experience_years = ?, consultation_fee = ?,
                available_days = ?, slot_start_time = ?, slot_end_time = ?, slot_duration_mins = ?, bio = ?
            WHERE user_id = ?
        """, (specialization, qualification, experience_years, consultation_fee, days_joined,
              slot_start_time, slot_end_time, slot_duration_mins, bio, user_id))
        conn.commit()
        flash('Your clinical schedule and profile details have been saved.', 'success')

    doctor = conn.execute("""
        SELECT d.*, dept.name as department_name, u.full_name, u.email, u.phone
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        JOIN departments dept ON d.department_id = dept.id
        WHERE d.user_id = ?
    """, (user_id,)).fetchone()
    conn.close()

    doctor_days = [d.strip() for d in doctor['available_days'].split(',')] if doctor['available_days'] else []
    all_weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    return render_template('doctor/schedule.html', doctor=doctor, doctor_days=doctor_days, all_weekdays=all_weekdays)
