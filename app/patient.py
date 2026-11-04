"""
Patient portal for MediFlow:
- Patient dashboard with stats and upcoming visits
- Doctor schedule browsing & time slot selection
- Conflict-safe appointment booking
- Reschedule & Cancel appointments
- Medical history & Prescriptions
- Profile editing
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import random
import datetime
from app.database import get_db_connection
from app.auth import login_required

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

def generate_appointment_number():
    """Generates a human-friendly unique appointment number like MDF-2026-4829."""
    year = datetime.datetime.now().year
    rand = random.randint(1000, 9999)
    return f"MDF-{year}-{rand}"

def generate_time_slots(start_time_str, end_time_str, duration_mins=30):
    """Generates list of HH:MM time slots between start and end time."""
    slots = []
    try:
        cur = datetime.datetime.strptime(start_time_str, "%H:%M")
        end = datetime.datetime.strptime(end_time_str, "%H:%M")
        while cur < end:
            slots.append(cur.strftime("%H:%M"))
            cur += datetime.timedelta(minutes=duration_mins)
    except Exception:
        slots = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00"]
    return slots

@patient_bp.route('/dashboard')
@login_required(role='patient')
def dashboard():
    """Patient overview dashboard."""
    conn = get_db_connection()
    user_id = session['user_id']
    
    patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (user_id,)).fetchone()
    if not patient:
        conn.close()
        flash('Patient record not found.', 'danger')
        return redirect(url_for('auth.logout'))

    patient_id = patient['id']

    # Fetch appointments
    appointments = conn.execute("""
        SELECT a.*, d.specialization, d.consultation_fee, u.full_name as doctor_name, dept.name as department_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN users u ON d.user_id = u.id
        JOIN departments dept ON d.department_id = dept.id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    """, (patient_id,)).fetchall()

    # Metrics
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    upcoming_count = sum(1 for a in appointments if a['appointment_date'] >= today_str and a['status'] in ('Scheduled', 'Rescheduled'))
    completed_count = sum(1 for a in appointments if a['status'] == 'Completed')
    total_count = len(appointments)

    conn.close()
    return render_template('patient/dashboard.html',
                           patient=patient,
                           appointments=appointments,
                           today_str=today_str,
                           upcoming_count=upcoming_count,
                           completed_count=completed_count,
                           total_count=total_count)

@patient_bp.route('/book', methods=['GET', 'POST'])
@login_required(role='patient')
def book_appointment():
    """Book a new appointment with a doctor."""
    conn = get_db_connection()
    user_id = session['user_id']
    patient = conn.execute("SELECT id FROM patients WHERE user_id = ?", (user_id,)).fetchone()

    preselected_doc_id = request.args.get('doctor_id', type=int)

    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id', type=int)
        appointment_date = request.form.get('appointment_date', '').strip()
        appointment_time = request.form.get('appointment_time', '').strip()
        symptoms = request.form.get('symptoms', '').strip()

        # Validation
        if not doctor_id or not appointment_date or not appointment_time:
            flash('Please select a doctor, consultation date, and available time slot.', 'warning')
            doctors = conn.execute("""
                SELECT d.*, u.full_name, dept.name as department_name
                FROM doctors d
                JOIN users u ON d.user_id = u.id
                JOIN departments dept ON d.department_id = dept.id
                ORDER BY u.full_name
            """).fetchall()
            conn.close()
            return render_template('patient/book.html', doctors=doctors, preselected_doc_id=doctor_id)

        # Check date not in the past
        try:
            chosen_date = datetime.datetime.strptime(appointment_date, '%Y-%m-%d').date()
            if chosen_date < datetime.date.today():
                flash('Appointment date cannot be in the past.', 'danger')
                doctors = conn.execute("""
                    SELECT d.*, u.full_name, dept.name as department_name
                    FROM doctors d
                    JOIN users u ON d.user_id = u.id
                    JOIN departments dept ON d.department_id = dept.id
                    ORDER BY u.full_name
                """).fetchall()
                conn.close()
                return render_template('patient/book.html', doctors=doctors, preselected_doc_id=doctor_id)
        except ValueError:
            flash('Invalid date format provided.', 'danger')
            doctors = conn.execute("""
                SELECT d.*, u.full_name, dept.name as department_name
                FROM doctors d
                JOIN users u ON d.user_id = u.id
                JOIN departments dept ON d.department_id = dept.id
                ORDER BY u.full_name
            """).fetchall()
            conn.close()
            return render_template('patient/book.html', doctors=doctors, preselected_doc_id=doctor_id)

        # Protection against duplicate appointment bookings for the doctor at that date/time
        existing_conflict = conn.execute("""
            SELECT id FROM appointments
            WHERE doctor_id = ? AND appointment_date = ? AND appointment_time = ? AND status IN ('Scheduled', 'Rescheduled')
        """, (doctor_id, appointment_date, appointment_time)).fetchone()

        if existing_conflict:
            flash('This time slot has just been booked by another patient. Please choose a different slot.', 'danger')
            doctors = conn.execute("""
                SELECT d.*, u.full_name, dept.name as department_name
                FROM doctors d
                JOIN users u ON d.user_id = u.id
                JOIN departments dept ON d.department_id = dept.id
                ORDER BY u.full_name
            """).fetchall()
            conn.close()
            return render_template('patient/book.html', doctors=doctors, preselected_doc_id=doctor_id)

        # Protection against patient booking overlapping appointment with another doctor
        patient_conflict = conn.execute("""
            SELECT id FROM appointments
            WHERE patient_id = ? AND appointment_date = ? AND appointment_time = ? AND status IN ('Scheduled', 'Rescheduled')
        """, (patient['id'], appointment_date, appointment_time)).fetchone()

        if patient_conflict:
            flash('You already have another active appointment scheduled at this exact time.', 'danger')
            doctors = conn.execute("""
                SELECT d.*, u.full_name, dept.name as department_name
                FROM doctors d
                JOIN users u ON d.user_id = u.id
                JOIN departments dept ON d.department_id = dept.id
                ORDER BY u.full_name
            """).fetchall()
            conn.close()
            return render_template('patient/book.html', doctors=doctors, preselected_doc_id=doctor_id)

        # Insert new appointment
        appt_num = generate_appointment_number()
        conn.execute("""
            INSERT INTO appointments (appointment_number, patient_id, doctor_id, appointment_date, appointment_time, status, symptoms)
            VALUES (?, ?, ?, ?, ?, 'Scheduled', ?)
        """, (appt_num, patient['id'], doctor_id, appointment_date, appointment_time, symptoms))
        conn.commit()
        conn.close()

        flash(f'Appointment {appt_num} confirmed successfully! Our clinical staff looks forward to assisting you.', 'success')
        return redirect(url_for('patient.dashboard'))

    doctors = conn.execute("""
        SELECT d.*, u.full_name, dept.name as department_name
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        JOIN departments dept ON d.department_id = dept.id
        ORDER BY u.full_name
    """).fetchall()
    conn.close()

    min_date = datetime.date.today().strftime('%Y-%m-%d')
    max_date = (datetime.date.today() + datetime.timedelta(days=60)).strftime('%Y-%m-%d')

    return render_template('patient/book.html', doctors=doctors, preselected_doc_id=preselected_doc_id, min_date=min_date, max_date=max_date)

@patient_bp.route('/api/doctor-slots/<int:doctor_id>')
def get_doctor_slots(doctor_id):
    """API endpoint to fetch available slots for a chosen doctor and date."""
    date_str = request.args.get('date', '').strip()
    if not date_str:
        return jsonify({'error': 'Date parameter required'}), 400

    conn = get_db_connection()
    doctor = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
    if not doctor:
        conn.close()
        return jsonify({'error': 'Doctor not found'}), 404

    # Generate all doctor slots
    all_slots = generate_time_slots(doctor['slot_start_time'], doctor['slot_end_time'], doctor['slot_duration_mins'])

    # Find booked slots
    booked_rows = conn.execute("""
        SELECT appointment_time FROM appointments
        WHERE doctor_id = ? AND appointment_date = ? AND status IN ('Scheduled', 'Rescheduled')
    """, (doctor_id, date_str)).fetchall()
    conn.close()

    booked_slots = set(row['appointment_time'] for row in booked_rows)
    available_slots = [s for s in all_slots if s not in booked_slots]

    return jsonify({
        'all_slots': all_slots,
        'booked_slots': list(booked_slots),
        'available_slots': available_slots,
        'consultation_fee': doctor['consultation_fee'],
        'available_days': doctor['available_days']
    })

@patient_bp.route('/reschedule/<int:appointment_id>', methods=['GET', 'POST'])
@login_required(role='patient')
def reschedule(appointment_id):
    """Patient rescheduling an existing appointment."""
    conn = get_db_connection()
    user_id = session['user_id']
    patient = conn.execute("SELECT id FROM patients WHERE user_id = ?", (user_id,)).fetchone()

    appt = conn.execute("""
        SELECT a.*, d.id as doc_id, d.slot_start_time, d.slot_end_time, d.slot_duration_mins, u.full_name as doctor_name, dept.name as department_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        JOIN users u ON d.user_id = u.id
        JOIN departments dept ON d.department_id = dept.id
        WHERE a.id = ? AND a.patient_id = ?
    """, (appointment_id, patient['id'])).fetchone()

    if not appt:
        conn.close()
        flash('Appointment not found or unauthorized.', 'danger')
        return redirect(url_for('patient.dashboard'))

    if appt['status'] not in ('Scheduled', 'Rescheduled'):
        conn.close()
        flash(f'Cannot reschedule an appointment that is already {appt["status"]}.', 'warning')
        return redirect(url_for('patient.dashboard'))

    if request.method == 'POST':
        new_date = request.form.get('appointment_date', '').strip()
        new_time = request.form.get('appointment_time', '').strip()

        if not new_date or not new_time:
            flash('Please select both a new date and time slot.', 'warning')
        else:
            # Check conflict
            conflict = conn.execute("""
                SELECT id FROM appointments
                WHERE doctor_id = ? AND appointment_date = ? AND appointment_time = ?
                  AND status IN ('Scheduled', 'Rescheduled') AND id != ?
            """, (appt['doc_id'], new_date, new_time, appointment_id)).fetchone()

            if conflict:
                flash('The selected time slot is already taken. Please choose another.', 'danger')
            else:
                conn.execute("""
                    UPDATE appointments
                    SET appointment_date = ?, appointment_time = ?, status = 'Rescheduled', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_date, new_time, appointment_id))
                conn.commit()
                conn.close()
                flash(f'Appointment {appt["appointment_number"]} has been successfully rescheduled.', 'success')
                return redirect(url_for('patient.dashboard'))

    min_date = datetime.date.today().strftime('%Y-%m-%d')
    max_date = (datetime.date.today() + datetime.timedelta(days=60)).strftime('%Y-%m-%d')
    conn.close()

    return render_template('patient/reschedule.html', appt=appt, min_date=min_date, max_date=max_date)

@patient_bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required(role='patient')
def cancel_appointment(appointment_id):
    """Patient cancels their scheduled appointment."""
    conn = get_db_connection()
    user_id = session['user_id']
    patient = conn.execute("SELECT id FROM patients WHERE user_id = ?", (user_id,)).fetchone()

    appt = conn.execute("SELECT * FROM appointments WHERE id = ? AND patient_id = ?", (appointment_id, patient['id'])).fetchone()
    if not appt:
        conn.close()
        flash('Appointment not found.', 'danger')
        return redirect(url_for('patient.dashboard'))

    if appt['status'] == 'Cancelled':
        conn.close()
        flash('This appointment is already cancelled.', 'info')
        return redirect(url_for('patient.dashboard'))

    conn.execute("UPDATE appointments SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()

    flash(f'Appointment {appt["appointment_number"]} has been cancelled.', 'info')
    return redirect(url_for('patient.dashboard'))

@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required(role='patient')
def profile():
    """View and update patient clinical demographic profile."""
    conn = get_db_connection()
    user_id = session['user_id']

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        dob = request.form.get('dob', '').strip()
        gender = request.form.get('gender', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        address = request.form.get('address', '').strip()
        emergency_contact = request.form.get('emergency_contact', '').strip()

        conn.execute("UPDATE users SET full_name = ?, phone = ? WHERE id = ?", (full_name, phone, user_id))
        conn.execute("""
            UPDATE patients
            SET dob = ?, gender = ?, blood_group = ?, address = ?, emergency_contact = ?
            WHERE user_id = ?
        """, (dob, gender, blood_group, address, emergency_contact, user_id))
        conn.commit()
        session['full_name'] = full_name
        flash('Your profile details have been updated successfully.', 'success')

    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()

    return render_template('patient/profile.html', user=user, patient=patient)
