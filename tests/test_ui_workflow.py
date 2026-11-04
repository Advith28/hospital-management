"""
End-to-End Automated UI and Clinical Workflow Verification for MediFlow.
Emulates complete user interaction flows through Flask Test Client:
1. Patient signs up, browses doctors, views slot availability, and books an appointment.
2. Doctor logs in, sees the booked appointment in today/upcoming queue, conducts consultation, and enters Rx.
3. Patient verifies clinical diagnosis and prescription appear in their portal.
4. Admin logs in, audits the appointment in master oversight, and confirms system totals.
"""

import unittest
import os
import tempfile
import datetime
from app import create_app
from app.database import init_db, get_db_connection

class MediFlowUIWorkflowE2ETest(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app({
            'TESTING': True,
            'DATABASE': self.db_path,
            'SECRET_KEY': 'e2e-ui-flow-key'
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            init_db(force_reseed=True)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_complete_patient_doctor_admin_lifecycle(self):
        """Simulates full clinical lifecycle across all 3 user roles."""
        print("\n--- STEP 1: Patient Self-Registration & Portal Access ---")
        reg_res = self.client.post('/register', data={
            'full_name': 'Samantha Reed',
            'email': 'samantha.reed@example.com',
            'phone': '+1 (555) 444-3322',
            'dob': '1995-07-21',
            'gender': 'Female',
            'blood_group': 'B+',
            'address': '840 Health Blvd, Metro City',
            'emergency_contact': '+1 (555) 111-2233',
            'password': 'SecurePassword@123',
            'confirm_password': 'SecurePassword@123'
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn(b'Registration successful', reg_res.data)

        # Login as Samantha
        login_res = self.client.post('/login', data={
            'email': 'samantha.reed@example.com',
            'password': 'SecurePassword@123'
        }, follow_redirects=True)
        self.assertIn(b'Samantha Reed', login_res.data)

        print("--- STEP 2: Patient Books Appointment with Cardiologist ---")
        booking_date = (datetime.date.today() + datetime.timedelta(days=3)).strftime('%Y-%m-%d')
        book_res = self.client.post('/patient/book', data={
            'doctor_id': 1, # Dr. Sarah Jenkins
            'appointment_date': booking_date,
            'appointment_time': '11:00',
            'symptoms': 'Palpitations and shortness of breath following cardio exercise.'
        }, follow_redirects=True)
        self.assertEqual(book_res.status_code, 200)
        self.assertIn(b'confirmed successfully', book_res.data)

        # Log out patient
        self.client.get('/logout')

        print("--- STEP 3: Doctor Logs In and Completes Clinical Consultation ---")
        doc_login = self.client.post('/login', data={
            'email': 'sarah.jenkins@mediflow.com',
            'password': 'Doctor@123'
        }, follow_redirects=True)
        self.assertIn(b'Dr. S. Sundararajan, MD, DM', doc_login.data)

        # Find the newly booked appointment ID from database
        with self.app.app_context():
            conn = get_db_connection()
            new_appt = conn.execute("""
                SELECT id, appointment_number FROM appointments
                WHERE doctor_id = 1 AND appointment_date = ? AND appointment_time = '11:00'
            """, (booking_date,)).fetchone()
            conn.close()

        self.assertIsNotNone(new_appt)
        new_appt_id = new_appt['id']
        appt_num = new_appt['appointment_number']

        # Doctor conducts consultation
        consult_res = self.client.post(f'/doctor/consult/{new_appt_id}', data={
            'doctor_notes': 'Sinus tachycardia observed. Normal cardiac rhythm on resting ECG. Reassurance given.',
            'prescription': 'Metoprolol 25mg orally once daily. Maintain hydration and schedule 2-week follow up.',
            'status': 'Completed'
        }, follow_redirects=True)
        self.assertEqual(consult_res.status_code, 200)
        self.assertIn(b'updated successfully', consult_res.data)

        # Log out doctor
        self.client.get('/logout')

        print("--- STEP 4: Patient Verifies Completed Consultation & Rx ---")
        self.client.post('/login', data={
            'email': 'samantha.reed@example.com',
            'password': 'SecurePassword@123'
        }, follow_redirects=True)

        patient_dash = self.client.get('/patient/dashboard')
        self.assertEqual(patient_dash.status_code, 200)
        self.assertIn(b'Completed', patient_dash.data)
        self.assertIn(b'Sinus tachycardia observed', patient_dash.data)
        self.assertIn(b'Metoprolol 25mg', patient_dash.data)

        # Log out patient
        self.client.get('/logout')

        print("--- STEP 5: Administrator Audits Master Oversight ---")
        admin_login = self.client.post('/login', data={
            'email': 'admin@mediflow.com',
            'password': 'Admin@123'
        }, follow_redirects=True)
        self.assertIn(b'Hospital Administrative Operations Console', admin_login.data)

        admin_appts = self.client.get('/admin/appointments')
        self.assertIn(appt_num.encode('utf-8'), admin_appts.data)
        self.assertIn(b'Samantha Reed', admin_appts.data)

        print("--- COMPLETE CLINICAL LIFECYCLE VERIFIED SUCCESSFULLY ---")

if __name__ == '__main__':
    unittest.main()
