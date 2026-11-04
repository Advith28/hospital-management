"""
Comprehensive Automated Test Suite for MediFlow Hospital Appointment Management System.
Includes:
- Positive test cases (happy path registration, login, appointment booking, rescheduling, consultation notes)
- Negative test cases (duplicate registration, invalid credentials, unauthorized role access, double booking attempt)
- Boundary test cases (past dates, password length boundary, slot edge times)
"""

import unittest
import os
import tempfile
import json
import datetime
from werkzeug.security import generate_password_hash
from app import create_app
from app.database import init_db, get_db_connection

class MediFlowTestSuite(unittest.TestCase):
    def setUp(self):
        """Set up an isolated test database and test client."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Override DB path dynamically for tests
        import app.database
        self.original_db_path = app.database.DB_PATH
        app.database.DB_PATH = self.db_path

        self.app = create_app({
            'TESTING': True,
            'DATABASE': self.db_path,
            'SECRET_KEY': 'test-secret-key-123',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()

        # Seed schema and test data into test database
        with self.app.app_context():
            init_db(force_reseed=True)

    def tearDown(self):
        """Clean up isolated database file."""
        import app.database
        app.database.DB_PATH = self.original_db_path
        os.close(self.db_fd)
        os.unlink(self.db_path)

    # ==========================================================
    # MODULE 1: AUTHENTICATION & ACCESS CONTROL TESTS
    # ==========================================================

    def test_pos_user_login_admin(self):
        """[POSITIVE] Admin logs in with valid credentials and receives dashboard redirect."""
        response = self.client.post('/login', data={
            'email': 'admin@mediflow.com',
            'password': 'Admin@123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Hospital Administrative Operations Console', response.data)

    def test_pos_patient_registration_and_login(self):
        """[POSITIVE] New patient registers and successfully authenticates."""
        reg_res = self.client.post('/register', data={
            'full_name': 'Grace Hopper',
            'email': 'grace.hopper@example.com',
            'password': 'Password@123',
            'confirm_password': 'Password@123',
            'phone': '+1 (555) 777-8888',
            'dob': '1990-12-09',
            'gender': 'Female',
            'blood_group': 'O+',
            'address': '100 Computer Way',
            'emergency_contact': '+1 (555) 000-1111'
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn(b'Registration successful', reg_res.data)

        # Login with newly created user
        login_res = self.client.post('/login', data={
            'email': 'grace.hopper@example.com',
            'password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Grace Hopper', login_res.data)

    def test_neg_login_invalid_password(self):
        """[NEGATIVE] Attempt login with wrong password."""
        res = self.client.post('/login', data={
            'email': 'admin@mediflow.com',
            'password': 'WrongPasswordXYZ'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Invalid email address or password', res.data)

    def test_neg_registration_duplicate_email(self):
        """[NEGATIVE] Attempt registration with an already registered email."""
        res = self.client.post('/register', data={
            'full_name': 'Duplicate User',
            'email': 'alex.rivera@example.com', # Pre-seeded patient
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'already exists', res.data)

    def test_neg_unauthorized_role_access(self):
        """[NEGATIVE] Patient cannot access restricted Admin dashboard."""
        # Login as patient
        self.client.post('/login', data={
            'email': 'alex.rivera@example.com',
            'password': 'Patient@123'
        })
        # Try accessing admin dashboard
        res = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Access denied', res.data)

    def test_boundary_password_length(self):
        """[BOUNDARY] Password shorter than 6 characters is rejected."""
        res = self.client.post('/register', data={
            'full_name': 'Short Pass',
            'email': 'short@example.com',
            'password': '12345', # 5 chars
            'confirm_password': '12345'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Password must be at least 6 characters long', res.data)

    # ==========================================================
    # MODULE 2: APPOINTMENT SCHEDULING & CONFLICTS TESTS
    # ==========================================================

    def test_pos_book_appointment(self):
        """[POSITIVE] Patient books an available slot with doctor."""
        self.client.post('/login', data={'email': 'alex.rivera@example.com', 'password': 'Patient@123'})
        
        target_date = (datetime.date.today() + datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        res = self.client.post('/patient/book', data={
            'doctor_id': 1,
            'appointment_date': target_date,
            'appointment_time': '14:00',
            'symptoms': 'Routine blood pressure review'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'confirmed successfully', res.data)

    def test_neg_duplicate_double_booking_prevention(self):
        """[NEGATIVE] Two patients cannot book the same doctor at the exact same date & time."""
        target_date = (datetime.date.today() + datetime.timedelta(days=10)).strftime('%Y-%m-%d')

        # Patient 1 books 10:00 AM slot
        self.client.post('/login', data={'email': 'alex.rivera@example.com', 'password': 'Patient@123'})
        res1 = self.client.post('/patient/book', data={
            'doctor_id': 1,
            'appointment_date': target_date,
            'appointment_time': '10:00',
            'symptoms': 'Cardiac checkup'
        }, follow_redirects=True)
        self.assertIn(b'confirmed successfully', res1.data)
        self.client.get('/logout')

        # Patient 2 tries to book the same doctor and same slot
        self.client.post('/login', data={'email': 'clara.oswald@example.com', 'password': 'Patient@123'})
        res2 = self.client.post('/patient/book', data={
            'doctor_id': 1,
            'appointment_date': target_date,
            'appointment_time': '10:00',
            'symptoms': 'Need cardiac consultation'
        }, follow_redirects=True)
        self.assertIn(b'This time slot has just been booked by another patient', res2.data)

    def test_boundary_past_date_appointment_booking(self):
        """[BOUNDARY] Booking with a date in the past is rejected."""
        self.client.post('/login', data={'email': 'alex.rivera@example.com', 'password': 'Patient@123'})
        past_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        res = self.client.post('/patient/book', data={
            'doctor_id': 1,
            'appointment_date': past_date,
            'appointment_time': '10:00',
            'symptoms': 'Checkup'
        }, follow_redirects=True)
        self.assertIn(b'Appointment date cannot be in the past', res.data)

    def test_pos_reschedule_appointment(self):
        """[POSITIVE] Patient successfully reschedules their scheduled appointment."""
        self.client.post('/login', data={'email': 'alex.rivera@example.com', 'password': 'Patient@123'})
        
        # Pre-seeded appointment ID 1
        new_date = (datetime.date.today() + datetime.timedelta(days=12)).strftime('%Y-%m-%d')
        res = self.client.post('/patient/reschedule/1', data={
            'appointment_date': new_date,
            'appointment_time': '11:30'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'successfully rescheduled', res.data)

    def test_pos_cancel_appointment(self):
        """[POSITIVE] Patient cancels their scheduled appointment."""
        self.client.post('/login', data={'email': 'alex.rivera@example.com', 'password': 'Patient@123'})
        res = self.client.post('/patient/cancel/1', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'has been cancelled', res.data)

    # ==========================================================
    # MODULE 3: DOCTOR CLINICAL CONSULTATION & NOTES TESTS
    # ==========================================================

    def test_pos_doctor_record_diagnosis_and_prescription(self):
        """[POSITIVE] Doctor logs clinical notes and medication prescription."""
        self.client.post('/login', data={'email': 'sarah.jenkins@mediflow.com', 'password': 'Doctor@123'})
        
        # Appointment 1 is with Dr. Sarah Jenkins
        res = self.client.post('/doctor/consult/1', data={
            'doctor_notes': 'Blood pressure elevated at 145/95. Advised dietary sodium restriction.',
            'prescription': 'Amlodipine 5mg once daily in morning x 30 days.',
            'status': 'Completed'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'updated successfully', res.data)

        # Verify database record updated
        conn = get_db_connection()
        appt = conn.execute("SELECT * FROM appointments WHERE id = 1").fetchone()
        conn.close()
        self.assertEqual(appt['status'], 'Completed')
        self.assertIn('Amlodipine', appt['prescription'])

    def test_pos_doctor_schedule_update(self):
        """[POSITIVE] Doctor updates consultation fee and working days."""
        self.client.post('/login', data={'email': 'sarah.jenkins@mediflow.com', 'password': 'Doctor@123'})
        res = self.client.post('/doctor/schedule', data={
            'specialization': 'Senior Interventional Cardiology',
            'qualification': 'MD, FACC, FSCAI',
            'experience_years': 15,
            'consultation_fee': 950.00,
            'days': ['Monday', 'Tuesday', 'Wednesday'],
            'slot_start_time': '08:30',
            'slot_end_time': '16:00',
            'slot_duration_mins': 30,
            'bio': 'Updated cardiologist profile biography.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'saved', res.data)

    # ==========================================================
    # MODULE 4: ADMIN OPERATIONS TESTS
    # ==========================================================

    def test_pos_admin_create_doctor(self):
        """[POSITIVE] Admin creates a new doctor profile."""
        self.client.post('/login', data={'email': 'admin@mediflow.com', 'password': 'Admin@123'})
        res = self.client.post('/admin/doctors', data={
            'full_name': 'Dr. Gregory House, MD',
            'email': 'gregory.house@mediflow.com',
            'password': 'Doctor@123',
            'department_id': 1,
            'specialization': 'Diagnostic Medicine & Nephrology',
            'qualification': 'MD - Johns Hopkins',
            'experience_years': 20,
            'consultation_fee': 1200.00,
            'phone': '+1 (555) 911-0000',
            'bio': 'Specialist in rare and complex diagnostic cases.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'created successfully', res.data)

    def test_pos_admin_status_override(self):
        """[POSITIVE] Admin manually updates an appointment status."""
        self.client.post('/login', data={'email': 'admin@mediflow.com', 'password': 'Admin@123'})
        res = self.client.post('/admin/appointments/status/1', data={
            'status': 'Cancelled'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'status changed to Cancelled', res.data)

    # ==========================================================
    # MODULE 5: PUBLIC DIRECTORY & API TESTS
    # ==========================================================

    def test_pos_doctors_search_filter(self):
        """[POSITIVE] Public search filter returns matching doctor."""
        res = self.client.get('/doctors?search=Sundararajan')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Sundararajan', res.data)

    def test_pos_doctor_slots_api(self):
        """[POSITIVE] Slots JSON API returns available slots list."""
        self.client.post('/login', data={'email': 'alex.rivera@example.com', 'password': 'Patient@123'})
        target_date = (datetime.date.today() + datetime.timedelta(days=5)).strftime('%Y-%m-%d')
        res = self.client.get(f'/patient/api/doctor-slots/1?date={target_date}')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('all_slots', data)
        self.assertIn('available_slots', data)
        self.assertTrue(len(data['all_slots']) > 0)

if __name__ == '__main__':
    unittest.main()
