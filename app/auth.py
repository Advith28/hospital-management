"""
Authentication routes for MediFlow: Login, Register, Profile, Logout.
Includes session handling, password hashing, and role checks.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from app.database import get_db_connection

auth_bp = Blueprint('auth', __name__)

def login_required(role=None):
    """Decorator to enforce authenticated session and optional role authorization."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.path))
            
            if role and session.get('role') != role:
                flash(f'Access denied. Authorized for {role.capitalize()} only.', 'danger')
                # Redirect to appropriate home based on current role
                user_role = session.get('role')
                if user_role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user_role == 'doctor':
                    return redirect(url_for('doctor.dashboard'))
                else:
                    return redirect(url_for('patient.dashboard'))
                    
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles unified login for patients, doctors, and administrators."""
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        return redirect(url_for('patient.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please provide both email address and password.', 'warning')
            return render_template('auth/login.html', email=email)

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            # Session assignment
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            session['email'] = user['email']

            flash(f'Welcome back, {user["full_name"]}!', 'success')
            
            # Check redirect next param
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)

            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user['role'] == 'doctor':
                return redirect(url_for('doctor.dashboard'))
            else:
                return redirect(url_for('patient.dashboard'))
        else:
            flash('Invalid email address or password. Please verify your credentials.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Allows new patients to self-register with clinical demographic fields."""
    if 'user_id' in session:
        return redirect(url_for('patient.dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        dob = request.form.get('dob', '').strip()
        gender = request.form.get('gender', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        address = request.form.get('address', '').strip()
        emergency_contact = request.form.get('emergency_contact', '').strip()

        # Validation checks
        if not full_name or not email or not password:
            flash('Full Name, Email, and Password are required fields.', 'warning')
            return render_template('auth/register.html', form_data=request.form)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return render_template('auth/register.html', form_data=request.form)

        if password != confirm_password:
            flash('Passwords do not match. Please retype carefully.', 'danger')
            return render_template('auth/register.html', form_data=request.form)

        conn = get_db_connection()
        existing = conn.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
        if existing:
            conn.close()
            flash('An account with this email address already exists. Please login.', 'warning')
            return render_template('auth/register.html', form_data=request.form)

        try:
            hashed = generate_password_hash(password)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (role, email, password_hash, full_name, phone)
                VALUES ('patient', ?, ?, ?, ?)
            """, (email, hashed, full_name, phone))
            user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO patients (user_id, dob, gender, blood_group, address, emergency_contact)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, dob, gender, blood_group, address, emergency_contact))

            conn.commit()
            conn.close()

            flash('Registration successful! You may now sign in to your MediFlow account.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            conn.rollback()
            conn.close()
            flash(f'Registration error: {str(e)}', 'danger')
            return render_template('auth/register.html', form_data=request.form)

    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    """Logs out the user and clears session."""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))
