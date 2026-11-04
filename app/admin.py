"""
Administrator portal for MediFlow:
- Complete administrative dashboard with system stats
- Doctor management (Add, View, Edit, Remove)
- Patient registry & clinical history view
- Master appointment oversight (Filter by date, status, cancel, reschedule)
- Department management (Add, Edit, View counts)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash
import datetime
from app.database import get_db_connection
from app.auth import login_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required(role='admin')
def dashboard():
    """Admin high-level executive dashboard."""
    conn = get_db_connection()

    total_doctors = conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
    total_patients = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    total_appointments = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
    total_departments = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]

    scheduled_count = conn.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Scheduled'").fetchone()[0]
    completed_count = conn.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Completed'").fetchone()[0]
    cancelled_count = conn.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Cancelled'").fetchone()[0]

    # Recent appointments
    recent_appts = conn.execute("""
        SELECT a.*, p_u.full_name as patient_name, d_u.full_name as doctor_name, dept.name as department_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users p_u ON p.user_id = p_u.id
        JOIN doctors d ON a.doctor_id = d.id
        JOIN users d_u ON d.user_id = d_u.id
        JOIN departments dept ON d.department_id = dept.id
        ORDER BY a.created_at DESC
        LIMIT 8
    """).fetchall()

    # Department breakdown
    dept_stats = conn.execute("""
        SELECT dept.name, COUNT(d.id) as doctor_count, COUNT(a.id) as appt_count
        FROM departments dept
        LEFT JOIN doctors d ON dept.id = d.department_id
        LEFT JOIN appointments a ON d.id = a.doctor_id
        GROUP BY dept.id
        ORDER BY appt_count DESC
    """).fetchall()

    conn.close()

    return render_template('admin/dashboard.html',
                           total_doctors=total_doctors,
                           total_patients=total_patients,
                           total_appointments=total_appointments,
                           total_departments=total_departments,
                           scheduled_count=scheduled_count,
                           completed_count=completed_count,
                           cancelled_count=cancelled_count,
                           recent_appts=recent_appts,
                           dept_stats=dept_stats)

@admin_bp.route('/doctors', methods=['GET', 'POST'])
@login_required(role='admin')
def doctors():
    """List doctors and create new doctor profiles."""
    conn = get_db_connection()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', 'Doctor@123')
        phone = request.form.get('phone', '').strip()
        department_id = request.form.get('department_id', type=int)
        specialization = request.form.get('specialization', '').strip()
        qualification = request.form.get('qualification', '').strip()
        experience_years = request.form.get('experience_years', type=int) or 1
        consultation_fee = request.form.get('consultation_fee', type=float) or 500.0
        available_days = request.form.get('available_days', 'Monday, Tuesday, Wednesday, Thursday, Friday').strip()
        slot_start_time = request.form.get('slot_start_time', '09:00')
        slot_end_time = request.form.get('slot_end_time', '17:00')
        bio = request.form.get('bio', '').strip()

        if not full_name or not email or not department_id or not specialization:
            flash('Doctor name, email, department, and specialization are required.', 'warning')
        else:
            existing = conn.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
            if existing:
                flash('A user with this email address already exists in the system.', 'danger')
            else:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (role, email, password_hash, full_name, phone)
                    VALUES ('doctor', ?, ?, ?, ?)
                """, (email, generate_password_hash(password), full_name, phone))
                u_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO doctors (user_id, department_id, specialization, qualification, experience_years, consultation_fee, available_days, slot_start_time, slot_end_time, bio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (u_id, department_id, specialization, qualification, experience_years, consultation_fee, available_days, slot_start_time, slot_end_time, bio))
                conn.commit()
                flash(f'Doctor profile for {full_name} created successfully with default password "{password}".', 'success')
                return redirect(url_for('admin.doctors'))

    doctors_list = conn.execute("""
        SELECT d.*, u.full_name, u.email, u.phone, dept.name as department_name,
               COUNT(a.id) as appointment_count
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        JOIN departments dept ON d.department_id = dept.id
        LEFT JOIN appointments a ON d.id = a.doctor_id
        GROUP BY d.id
        ORDER BY u.full_name ASC
    """).fetchall()

    departments = conn.execute("SELECT * FROM departments ORDER BY name ASC").fetchall()
    conn.close()

    return render_template('admin/doctors.html', doctors=doctors_list, departments=departments)

@admin_bp.route('/doctors/delete/<int:doctor_id>', methods=['POST'])
@login_required(role='admin')
def delete_doctor(doctor_id):
    """Delete doctor account."""
    conn = get_db_connection()
    doc = conn.execute("SELECT user_id FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
    if doc:
        conn.execute("DELETE FROM users WHERE id = ?", (doc['user_id'],))
        conn.commit()
        flash('Doctor removed from the hospital roster.', 'info')
    conn.close()
    return redirect(url_for('admin.doctors'))

@admin_bp.route('/patients')
@login_required(role='admin')
def patients():
    """List registered patients with visit history metrics."""
    conn = get_db_connection()
    patients_list = conn.execute("""
        SELECT p.*, u.full_name, u.email, u.phone, u.created_at as registered_on,
               COUNT(a.id) as total_appointments
        FROM patients p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN appointments a ON p.id = a.patient_id
        GROUP BY p.id
        ORDER BY u.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('admin/patients.html', patients=patients_list)

@admin_bp.route('/appointments')
@login_required(role='admin')
def appointments():
    """Master appointment overview with filtering and management actions."""
    status_filter = request.args.get('status', '').strip()
    date_filter = request.args.get('date', '').strip()

    conn = get_db_connection()
    query = """
        SELECT a.*, p_u.full_name as patient_name, p_u.phone as patient_phone,
               d_u.full_name as doctor_name, dept.name as department_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN users p_u ON p.user_id = p_u.id
        JOIN doctors d ON a.doctor_id = d.id
        JOIN users d_u ON d.user_id = d_u.id
        JOIN departments dept ON d.department_id = dept.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND a.status = ?"
        params.append(status_filter)

    if date_filter:
        query += " AND a.appointment_date = ?"
        params.append(date_filter)

    query += " ORDER BY a.appointment_date DESC, a.appointment_time DESC"

    appointments_list = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('admin/appointments.html',
                           appointments=appointments_list,
                           status_filter=status_filter,
                           date_filter=date_filter)

@admin_bp.route('/appointments/status/<int:appointment_id>', methods=['POST'])
@login_required(role='admin')
def update_appointment_status(appointment_id):
    """Admin updates appointment status directly."""
    new_status = request.form.get('status')
    if new_status in ('Scheduled', 'Completed', 'Cancelled', 'Rescheduled'):
        conn = get_db_connection()
        conn.execute("UPDATE appointments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, appointment_id))
        conn.commit()
        conn.close()
        flash(f'Appointment status changed to {new_status}.', 'success')
    return redirect(url_for('admin.appointments'))

@admin_bp.route('/departments', methods=['GET', 'POST'])
@login_required(role='admin')
def departments():
    """Department management."""
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        icon = request.form.get('icon', 'stethoscope').strip()
        description = request.form.get('description', '').strip()

        if not name or not description:
            flash('Department name and description are required.', 'warning')
        else:
            try:
                conn.execute("INSERT INTO departments (name, icon, description) VALUES (?, ?, ?)", (name, icon, description))
                conn.commit()
                flash(f'Department "{name}" added successfully.', 'success')
            except Exception as e:
                flash(f'Could not add department: {str(e)}', 'danger')

    departments_list = conn.execute("""
        SELECT dept.*, COUNT(d.id) as doctor_count
        FROM departments dept
        LEFT JOIN doctors d ON dept.id = d.department_id
        GROUP BY dept.id
        ORDER BY dept.name ASC
    """).fetchall()
    conn.close()

    return render_template('admin/departments.html', departments=departments_list)
