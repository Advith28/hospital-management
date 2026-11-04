# MediFlow — Quality Assurance & Defect Log

## Test Execution Summary

- **Total Unit & Integration Tests:** 17 Passed / 0 Failed (100% Pass Rate)
- **End-to-End Workflow Tests:** 1 Passed / 0 Failed (100% Pass Rate)
- **Average Cyclomatic Complexity (McCabe Metric):** 3.74 (Target threshold < 6.0 — **Grade A**)
- **Test Framework:** Python `unittest` standard library runner with isolated SQLite test databases.

---

## Detailed Test Cases Matrix

| Test ID | Module | Category | Description | Input Conditions | Expected Outcome | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-AUTH-01** | Auth | Positive | Admin Login | `admin@mediflow.com` / `Admin@123` | Session created, role assigned to admin, redirected to admin dashboard | **PASS** |
| **TC-AUTH-02** | Auth | Positive | Patient Self-Registration | Full demographics, valid password | User & Patient records created in SQLite, redirect to login | **PASS** |
| **TC-AUTH-03** | Auth | Negative | Invalid Password | Correct email, wrong password | Rejection flash warning, session not created | **PASS** |
| **TC-AUTH-04** | Auth | Negative | Duplicate Email | Pre-existing email address | "already exists" error warning, prevented duplicate account | **PASS** |
| **TC-AUTH-05** | Auth | Negative | RBAC Privilege Boundary | Patient session accesses `/admin/dashboard` | Access denied flash warning, redirected to patient dashboard | **PASS** |
| **TC-AUTH-06** | Auth | Boundary | Password Length Minimum | Password with 5 characters | Rejection notice stating 6-character minimum threshold | **PASS** |
| **TC-APPT-01** | Booking | Positive | New Slot Booking | Valid doctor, valid future date & slot | Appointment record created with status `Scheduled` | **PASS** |
| **TC-APPT-02** | Booking | Negative | Double-Booking Prevention | 2 patients booking same doctor, date & time | Second attempt blocked with conflict error message | **PASS** |
| **TC-APPT-03** | Booking | Boundary | Past Date Booking | Appointment date < Current date | Rejection warning: "Appointment date cannot be in the past" | **PASS** |
| **TC-APPT-04** | Booking | Positive | Reschedule Consultation | Valid appointment ID, new open slot | Appointment date updated, status marked `Rescheduled` | **PASS** |
| **TC-APPT-05** | Booking | Positive | Cancellation | Active appointment ID | Status transitioned to `Cancelled`, slot freed | **PASS** |
| **TC-DOC-01** | Doctor | Positive | Consultation Notes & Rx | Doctor records observations + prescription | Appointment updated to `Completed`, Rx visible to patient | **PASS** |
| **TC-DOC-02** | Doctor | Positive | Practice Settings Update | Fee updated, consultation days toggled | Doctor profile and schedule timing successfully persisted | **PASS** |
| **TC-ADM-01** | Admin | Positive | Add Physician | Clinical details, specialization, fee | New doctor account + doctor profile created in database | **PASS** |
| **TC-ADM-02** | Admin | Positive | Status Override | Admin updates status dropdown | Appointment status changed across the hospital database | **PASS** |
| **TC-DIR-01** | Directory | Positive | Doctor Search | Query `Jenkins` | Search results correctly return Dr. Sarah Jenkins | **PASS** |
| **TC-API-01** | API | Positive | Doctor Slots API | Doctor ID + date query param | JSON returned with available slots & booked slots | **PASS** |
| **TC-E2E-01** | Full Flow | Positive | Multi-Role Lifecycle | Patient register -> Book -> Doctor consult -> Rx audit | Complete multi-step lifecycle verified end-to-end | **PASS** |

---

## Defect Log & Resolution History

| Defect ID | Severity | Discovery Phase | Description | Root Cause | Resolution Implemented | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-001** | High | Test Integration | Foreign key violation when inserting appointments during test fixture runs. | Test setup re-seeded database without clearing `sqlite_sequence`, resulting in mismatched doctor/patient auto-increment IDs. | Added explicit `DELETE FROM sqlite_sequence` in `database.seed_data()` and allowed dynamic test database injection. | **VERIFIED (Pass)** |
| **DEF-002** | Medium | Test Integration | Public slot booking preview blocked by 404/login requirement. | `get_doctor_slots` route had `@login_required(role='patient')` decorator preventing calendar preview prior to sign in. | Removed requirement for slot availability lookup so patients and guests can check availability freely. | **VERIFIED (Pass)** |
| **DEF-003** | Low | UI Flow | Duplicate patient simultaneous booking protection edge case. | Patients could theoretically book overlapping appointments with two different doctors at the same minute. | Implemented cross-doctor patient collision check `patient_conflict` query in `app/patient.py`. | **VERIFIED (Pass)** |
