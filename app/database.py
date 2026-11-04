"""
Database module for Kovai MetroCare General Hospital (Coimbatore).
Handles SQLite connection, table schemas, initialization, and sample seed data.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mediflow.db')

def get_db_connection():
    """Returns a SQLite connection with Row factory enabled for dictionary-like access."""
    from flask import current_app
    db_file = DB_PATH
    try:
        if current_app and 'DATABASE' in current_app.config:
            db_file = current_app.config['DATABASE']
    except RuntimeError:
        pass
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(force_reseed=False):
    """Initializes tables and seeds initial data if database is empty or force_reseed is True."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL CHECK(role IN ('admin', 'doctor', 'patient')),
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icon TEXT NOT NULL,
        description TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        department_id INTEGER NOT NULL,
        specialization TEXT NOT NULL,
        qualification TEXT NOT NULL,
        experience_years INTEGER NOT NULL DEFAULT 1,
        consultation_fee REAL NOT NULL DEFAULT 500.0,
        available_days TEXT NOT NULL, -- e.g. "Monday, Tuesday, Wednesday, Thursday, Friday"
        slot_start_time TEXT NOT NULL DEFAULT '09:00',
        slot_end_time TEXT NOT NULL DEFAULT '17:00',
        slot_duration_mins INTEGER NOT NULL DEFAULT 30,
        bio TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        dob TEXT,
        gender TEXT CHECK(gender IN ('Male', 'Female', 'Other')),
        blood_group TEXT,
        address TEXT,
        emergency_contact TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_number TEXT UNIQUE NOT NULL,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        appointment_date TEXT NOT NULL, -- YYYY-MM-DD
        appointment_time TEXT NOT NULL, -- HH:MM
        status TEXT NOT NULL DEFAULT 'Scheduled' CHECK(status IN ('Scheduled', 'Completed', 'Cancelled', 'Rescheduled')),
        symptoms TEXT,
        doctor_notes TEXT,
        prescription TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
        FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
        UNIQUE(doctor_id, appointment_date, appointment_time, status)
    );
    ''')
    conn.commit()

    # Check if admin already exists
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin'")
    has_admin = cursor.fetchone()['cnt'] > 0

    if not has_admin or force_reseed:
        seed_data(conn)

    conn.close()

def seed_data(conn):
    """Populates database with sample departments, doctors, patients, and appointments in Coimbatore, Tamil Nadu, India."""
    cursor = conn.cursor()

    # Clear existing if reseeding
    cursor.execute("DELETE FROM appointments")
    cursor.execute("DELETE FROM patients")
    cursor.execute("DELETE FROM doctors")
    cursor.execute("DELETE FROM departments")
    cursor.execute("DELETE FROM users")
    try:
        cursor.execute("DELETE FROM sqlite_sequence")
    except Exception:
        pass

    # 1. Seed Departments
    departments = [
        ("Cardiology", "heart-pulse", "Cardiovascular care, ECG, echo, hypertension management, and coronary diagnostics."),
        ("Neurology", "brain", "Brain, spine disorders, migraine therapy, stroke rehabilitation, and clinical neuropathy."),
        ("Orthopedics", "bone", "Joint replacement, fracture trauma care, arthroscopy, and musculoskeletal rehabilitation."),
        ("Pediatrics", "baby", "Child healthcare, newborn immunizations, pediatric nutrition, and developmental wellness."),
        ("Dermatology", "sparkles", "Clinical dermatology, psoriasis management, allergy testing, and aesthetic skin care."),
        ("General Medicine", "stethoscope", "Preventive master health checks, seasonal viral fevers, diabetes, and lifestyle medicine.")
    ]
    cursor.executemany("INSERT INTO departments (name, icon, description) VALUES (?, ?, ?)", departments)

    # 2. Seed Admin
    cursor.execute("""
        INSERT INTO users (role, email, password_hash, full_name, phone)
        VALUES (?, ?, ?, ?, ?)
    """, ('admin', 'admin@mediflow.com', generate_password_hash('Admin@123'), 'Dr. R. Senthil Kumar, MD (Medical Superintendent)', '+91 94431 20011'))

    # 3. Seed Doctors (Coimbatore Medical Specialists)
    dept_map = {row['name']: row['id'] for row in cursor.execute("SELECT id, name FROM departments").fetchall()}
    
    doctor_samples = [
        ('doctor', 'sarah.jenkins@mediflow.com', 'Doctor@123', 'Dr. S. Sundararajan, MD, DM', '+91 98422 11001',
         dept_map['Cardiology'], 'Senior Interventional Cardiologist', 'MBBS, MD (Gen Med), DM (Cardio) - MMC Chennai', 16, 700.0,
         'Monday, Tuesday, Wednesday, Thursday, Friday', '09:00', '16:30', 30,
         'Senior cardiologist with extensive expertise in preventive heart health, coronary angiograms, and hypertension management in Western Tamil Nadu.'),

        ('doctor', 'marcus.chen@mediflow.com', 'Doctor@123', 'Dr. M. Karthik, MD, DM', '+91 98422 22002',
         dept_map['Neurology'], 'Consultant Neurologist & Neurophysiologist', 'MBBS, MD, DM (Neuro) - NIMHANS Bengaluru', 12, 800.0,
         'Monday, Wednesday, Thursday, Friday', '10:00', '17:00', 30,
         'Specialized in chronic migraines, peripheral neuropathies, stroke management, and epilepsy care.'),

        ('doctor', 'elena.rodriguez@mediflow.com', 'Doctor@123', 'Dr. V. Rajeshwari, MS (Ortho)', '+91 98422 33003',
         dept_map['Orthopedics'], 'Consultant Orthopedic & Arthroscopy Surgeon', 'MBBS, MS (Ortho), DNB - CMC Vellore', 10, 650.0,
         'Tuesday, Wednesday, Thursday, Saturday', '09:00', '15:00', 30,
         'Focused on knee arthroscopy, sports ligament reconstruction, and geriatric joint preservation.'),

        ('doctor', 'priya.nair@mediflow.com', 'Doctor@123', 'Dr. Priya Nair, MD (Peds)', '+91 98422 44004',
         dept_map['Pediatrics'], 'Consultant Pediatrician & Neonatologist', 'MBBS, MD (Pediatrics) - AIIMS New Delhi', 9, 500.0,
         'Monday, Tuesday, Thursday, Friday, Saturday', '09:30', '16:30', 30,
         'Warm, child-friendly care specializing in newborn developmental milestones and pediatric immunizations.'),

        ('doctor', 'david.kim@mediflow.com', 'Doctor@123', 'Dr. D. Anand, MD (Derm)', '+91 98422 55005',
         dept_map['Dermatology'], 'Consultant Dermatologist & Dermatosurgeon', 'MBBS, MD (DVL) - JIPMER Puducherry', 11, 600.0,
         'Monday, Tuesday, Wednesday, Friday', '10:00', '16:00', 30,
         'Specialized in clinical allergy testing, eczema therapies, acne treatments, and laser procedures.'),

        ('doctor', 'robert.taylor@mediflow.com', 'Doctor@123', 'Dr. R. Balasubramanian, MD', '+91 98422 66006',
         dept_map['General Medicine'], 'Senior Physician & Diabetologist', 'MBBS, MD (Internal Medicine) - Coimbatore Medical College', 18, 450.0,
         'Monday, Tuesday, Wednesday, Thursday, Friday', '08:30', '16:00', 30,
         'Senior primary care physician with over 18 years treating chronic diabetes, fever diagnostics, and elderly healthcare.')
    ]

    for role, email, pwd, name, phone, dept_id, spec, qual, exp, fee, days, s_time, e_time, dur, bio in doctor_samples:
        cursor.execute("INSERT INTO users (role, email, password_hash, full_name, phone) VALUES (?, ?, ?, ?, ?)",
                       (role, email, generate_password_hash(pwd), name, phone))
        u_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO doctors (user_id, department_id, specialization, qualification, experience_years, consultation_fee, available_days, slot_start_time, slot_end_time, slot_duration_mins, bio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (u_id, dept_id, spec, qual, exp, fee, days, s_time, e_time, dur, bio))

    # 4. Seed Patients (Local Coimbatore Addresses & Indian names)
    patient_samples = [
        ('patient', 'alex.rivera@example.com', 'Patient@123', 'K. Vignesh', '+91 98430 11223',
         '1994-06-15', 'Male', 'O+', '45, Trichy Road, Singanallur, Coimbatore - 641005', '+91 98430 99001'),
        ('patient', 'clara.oswald@example.com', 'Patient@123', 'Deepa Jayaram', '+91 98430 22334',
         '1997-11-20', 'Female', 'B+', '12/4, Avinashi Road, Peelamedu, Coimbatore - 641004', '+91 98430 99002'),
        ('patient', 'james.wilson@example.com', 'Patient@123', 'M. Senthil Nathan', '+91 98430 33445',
         '1988-03-12', 'Male', 'A+', '88, Cross Cut Road, Gandhipuram, Coimbatore - 641012', '+91 98430 99003')
    ]

    patient_ids = []
    for role, email, pwd, name, phone, dob, gender, blood, addr, emg in patient_samples:
        cursor.execute("INSERT INTO users (role, email, password_hash, full_name, phone) VALUES (?, ?, ?, ?, ?)",
                       (role, email, generate_password_hash(pwd), name, phone))
        u_id = cursor.lastrowid
        cursor.execute("INSERT INTO patients (user_id, dob, gender, blood_group, address, emergency_contact) VALUES (?, ?, ?, ?, ?, ?)",
                       (u_id, dob, gender, blood, addr, emg))
        patient_ids.append(cursor.lastrowid)

    # 5. Seed Appointments
    doctor_ids = [row['id'] for row in cursor.execute("SELECT id FROM doctors ORDER BY id").fetchall()]
    
    appts = [
        ('MDF-2026-1001', patient_ids[0], doctor_ids[0], '2026-10-15', '09:30', 'Scheduled', 'Hypertension follow-up and resting ECG evaluation.', None, None),
        ('MDF-2026-1002', patient_ids[1], doctor_ids[1], '2026-10-16', '10:30', 'Scheduled', 'Frequent tension headaches and neck stiffness over 2 weeks.', None, None),
        ('MDF-2026-1003', patient_ids[2], doctor_ids[2], '2026-10-14', '11:00', 'Scheduled', 'Right knee pain after shuttle badminton game.', None, None),
        ('MDF-2026-0901', patient_ids[0], doctor_ids[5], '2026-09-28', '14:00', 'Completed', 'Viral fever symptoms, throat irritation, and fatigue.', 'Acute viral pharyngitis diagnosed. Temperature 99.8 F. Hydration advised.', 'Tab Paracetamol 650mg tid x 3 days, Vitamin C 500mg od x 5 days, Warm saline gargle.'),
        ('MDF-2026-0902', patient_ids[1], doctor_ids[4], '2026-09-30', '15:00', 'Completed', 'Allergic rash and itching on both forearms.', 'Contact dermatitis diagnosed. Avoid detergent exposure.', 'Tab Levocetirizine 5mg od (bedtime) x 5 days, Calamine lotion topical bid.')
    ]

    cursor.executemany("""
        INSERT INTO appointments (appointment_number, patient_id, doctor_id, appointment_date, appointment_time, status, symptoms, doctor_notes, prescription)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, appts)

    conn.commit()
    print("MediFlow database initialized and seeded successfully with Coimbatore Indian patient & doctor records.")

if __name__ == '__main__':
    init_db(force_reseed=True)
