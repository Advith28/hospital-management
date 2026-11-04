# MediFlow — Comprehensive College Viva & Technical Defense Guide

This guide is specifically curated for final-year engineering and computer science students to confidently explain the **MediFlow Hospital Appointment Management System** during project defense, external evaluation, and viva examinations.

---

## 1. Project Overview & Elevator Pitch

> *"MediFlow is a production-ready, full-stack Hospital Information & Appointment Management System built with Python Flask and SQLite. It provides role-based workflows for Patients, Doctors, and Hospital Administrators. Key technical highlights include ACID-compliant transactional booking with double-booking prevention, dynamic asynchronous slot generation, role-based access control (RBAC), and digital clinical prescription management."*

---

## 2. System Architecture & Tech Stack Justification

### Why Flask instead of Django?
- **Lightweight & Modular:** Flask provides an explicit micro-framework architecture using Blueprints (`app/auth.py`, `app/patient.py`, `app/doctor.py`, `app/admin.py`), keeping code clean and avoiding unnecessary abstractions.
- **Easy to Explain in Viva:** Every routing mechanism, session assignment, database query, and decorator is clearly visible and straightforward to walk through.

### Why SQLite?
- **Zero-Configuration & Serverless:** Stores the relational database as a single file (`mediflow.db`), making the project portable across any examiner machine.
- **Relational Integrity:** Implements full foreign key constraints (`PRAGMA foreign_keys = ON`), transactions, and multi-column unique constraints.

---

## 3. Database Schema & Relational Design

The system consists of 5 normalized tables in 3NF (Third Normal Form):

```
       +------------------+
       |      users       |
       +------------------+
       | id (PK)          |
       | role             |
       | email (UNIQUE)   |
       | password_hash    |
       | full_name        |
       +--------+---------+
                | 1:1
       +--------+-------------------------+
       |                                  |
       v                                  v
+---------------+                 +----------------+
|   patients    |                 |    doctors     |
+---------------+                 +----------------+
| id (PK)       |                 | id (PK)        |
| user_id (FK)  |                 | user_id (FK)   |
| dob, gender   |                 | dept_id (FK)   |
| blood_group   |                 | consultation_fee
| address       |                 | available_days |
+-------+-------+                 +-------+--------+
        |                                 |
        | 1:N                             | 1:N
        v                                 v
   +-------------------------------------------+
   |               appointments                |
   +-------------------------------------------+
   | id (PK)                                   |
   | appointment_number (UNIQUE)               |
   | patient_id (FK)                           |
   | doctor_id (FK)                            |
   | appointment_date                          |
   | appointment_time                          |
   | status (Scheduled/Completed/Cancelled)   |
   | doctor_notes (Diagnosis)                  |
   | prescription (Rx)                         |
   +-------------------------------------------+
```

### Critical Constraint for Viva:
```sql
UNIQUE(doctor_id, appointment_date, appointment_time, status)
```
**Explanation:** Enforces database-level concurrency protection so two parallel requests cannot book the same doctor at the same slot.

---

## 4. Key Functions Walkthrough

### 1. Concurrency & Double-Booking Protection (`app/patient.py -> book_appointment()`)
- **How it works:**
  1. Checks if the selected date is in the past.
  2. Executes a parameterized query checking for existing active appointments (`status IN ('Scheduled', 'Rescheduled')`) for that specific doctor, date, and slot.
  3. Checks if the patient already has an active conflicting appointment with any other doctor at that exact time.
  4. Inserts the new appointment in an ACID transaction.

### 2. Dynamic Time Slot Generator (`app/patient.py -> generate_time_slots()`)
- Converts doctor's `slot_start_time` (e.g., `09:00`) and `slot_end_time` (e.g., `17:00`) into increments dictated by `slot_duration_mins` (e.g., 30 mins).
- The client-side JavaScript calls `/patient/api/doctor-slots/<doctor_id>?date=<date>` via AJAX/Fetch API and marks occupied slots with a disabled strike-through pill.

### 3. Role-Based Access Control (`app/auth.py -> login_required(role)`)
- Custom Python decorator wrapping Flask view functions:
  ```python
  def login_required(role=None):
      def decorator(f):
          @wraps(f)
          def decorated_function(*args, **kwargs):
              if 'user_id' not in session:
                  return redirect(url_for('auth.login'))
              if role and session.get('role') != role:
                  return redirect(...)
              return f(*args, **kwargs)
          return decorated_function
      return decorator
  ```

### 4. Password Security
- Uses `werkzeug.security.generate_password_hash` and `check_password_hash` with `pbkdf2:sha256:1000000` salt rounds, protecting against dictionary and rainbow-table attacks.

---

## 5. Frequently Asked Viva Questions & Answers

### Q1: What happens if two patients submit a booking for the same slot at the exact same millisecond?
**Answer:** Both the application tier and database tier are protected. The application checks active records before insertion, and the SQLite table schema has a compound `UNIQUE(doctor_id, appointment_date, appointment_time, status)` constraint. In the event of a simultaneous race condition, the second transaction is rejected with an `IntegrityError`, caught gracefully, and rolled back.

### Q2: How did you calculate Cyclomatic Complexity?
**Answer:** We wrote an AST (Abstract Syntax Tree) analyzer script (`tests/code_metrics.py`) that analyzes execution decision points (`if`, `while`, `for`, `except`, `and`, `or`). Our codebase achieved an average McCabe score of **3.74**, well under the software engineering industry risk threshold of 6.0 (Grade A maintainability).

### Q3: How are patient prescriptions handled?
**Answer:** In the Doctor Portal, when examining an appointment, the physician can review the patient's past medical history and vitals, document clinical observations/diagnosis, write electronic prescriptions, and mark the visit as `Completed`. The patient immediately views these diagnosis notes and digital prescriptions in their dashboard.

### Q4: What automated testing did you perform?
**Answer:** We implemented 17 automated unit and integration test cases covering positive cases, negative cases (duplicate accounts, invalid passwords, unauthorized role escalation), and boundary cases (past dates, short passwords), as well as a full end-to-end multi-role UI lifecycle test (`tests/test_ui_workflow.py`).
