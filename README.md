# 🏥 MediFlow — Hospital Appointment Management System

A simple, complete web application built with **Python Flask** and **SQLite** for managing hospital appointments, patient records, and doctor schedules.

---

## ⚡ How to Run the Project (3 Steps)

### Step 1: Open Terminal
Open VS Code, press `Ctrl + \`` (or `Cmd + \`` on Mac) to open the built-in terminal, and make sure you are in the project folder.

### Step 2: Install Requirements
If you haven't installed Flask yet, run:
```bash
pip install flask werkzeug
```

### Step 3: Start the Application
Run:
```bash
python3 run.py
```
*(On Windows, you can type `python run.py`)*

Now open your web browser and go to:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Demo Login Accounts

The database comes pre-loaded with sample accounts so you can log in immediately:

| Role | Email | Password | What You Can Do |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@mediflow.com` | `Admin@123` | Manage doctors, view all hospital stats, manage all appointments |
| **Doctor** | `sarah.jenkins@mediflow.com` | `Doctor@123` | View today's patient queue, write diagnosis & digital prescriptions |
| **Patient** | `alex.rivera@example.com` | `Patient@123` | Book appointment slots, view doctors, check prescriptions |

> **Note:** You can also click **"Register as Patient"** on the website to create a brand new patient account.

---

## 💾 How to Show the Database to Evaluators

> ⚠️ **IMPORTANT:** Never open `mediflow.db` as a plain text file in VS Code! Because it is an SQLite database file, opening it directly displays raw binary symbols.

### Recommended Method: VS Code SQLite Viewer (Easiest)
1. In VS Code, open the **Extensions tab** (`Cmd + Shift + X` on Mac or `Ctrl + Shift + X` on Windows).
2. Search for **`SQLite Viewer`** (by *Florian Klampfer*) and click **Install**.
3. Now, whenever you click on **`mediflow.db`** in the left sidebar, it will open as a clean, interactive visual table (like Excel / MySQL Workbench) displaying all tables and records!

### Alternative 1: DB Browser for SQLite (GUI App)
1. Download and install [DB Browser for SQLite](https://sqlitebrowser.org/dl/) (free for Mac and Windows).
2. Click **Open Database** and choose `mediflow.db`.
3. Click the **Browse Data** tab to view `appointments`, `doctors`, `patients`, and `users`.

### Alternative 2: Terminal Commands
Run directly in your terminal:
```bash
sqlite3 mediflow.db
```
Inside the SQLite prompt:
```sql
.tables                                  -- shows all tables
.mode table                              -- formats output nicely
SELECT * FROM appointments;              -- shows all appointments
SELECT * FROM doctors;                   -- shows all doctors
.quit                                    -- exit SQLite
```

---

## 👥 Main Features by Role

### 1. 👤 Patient
* Register account with personal and medical details (Blood group, DOB, emergency contact).
* Browse and filter doctors by department and specialization.
* Select interactive appointment time slots.
* Cancel or reschedule existing appointments.
* View clinical diagnosis notes and prescriptions from doctors.

### 2. 🩺 Doctor
* View daily outpatient appointment schedule.
* Open consultation suite to record clinical diagnosis and prescribe medication.
* View patient's past medical and consultation history.
* Set consultation fees and clinic working hours.

### 3. 🛡️ Administrator
* Overview dashboard with real-time statistics (total doctors, patients, appointments).
* Add new doctors and assign departments and fees.
* View full registered patient registry.
* Master control to oversee, filter, and update status of any appointment.

---

## 📁 Simple Project Folder Guide

```text
Hospital appointment management system/
├── app/
│   ├── templates/          # HTML pages for Patient, Doctor, Admin, and Auth
│   ├── static/             # CSS styling and JavaScript logic
│   ├── auth.py             # Login, signup, and logout handling
│   ├── patient.py          # Patient booking and dashboard logic
│   ├── doctor.py           # Doctor consultation and schedule logic
│   ├── admin.py            # Admin operations and doctor roster logic
│   └── database.py         # Database connection and table creation
├── docs/
│   └── VIVA_PREPARATION_GUIDE.md  # Answers to common viva questions
├── tests/                  # Automated test files
├── mediflow.db             # SQLite database storing all project data
├── run.py                  # Main Python file to run the server
└── README.md               # This documentation file
```

---

## 🎓 Viva / Presentation Quick Summary

If the examiner asks:
* **What is the Tech Stack?**  
  Python (Flask framework) for backend, SQLite for database, HTML/CSS/JavaScript for frontend.
* **Why SQLite instead of MySQL?**  
  SQLite is lightweight, serverless, and stores all relational data in a single file (`mediflow.db`), making it fast, portable, and zero-maintenance while supporting standard SQL queries and foreign keys.
* **What are the Database Tables?**  
  1. `users` (Login info: email, password hash, role)
  2. `patients` (Medical info: DOB, blood group, address)
  3. `doctors` (Specialization, fee, timing, department)
  4. `departments` (Cardiology, Neurology, Pediatrics, etc.)
  5. `appointments` (Date, slot time, status, diagnosis, prescription)
* **How are passwords stored?**  
  Securely hashed using `PBKDF2-SHA256` (passwords are never saved in plain text).

*(For a deeper list of 20+ viva questions with ready answers, check [docs/VIVA_PREPARATION_GUIDE.md](docs/VIVA_PREPARATION_GUIDE.md))*
