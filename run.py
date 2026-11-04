"""
MediFlow Application Entry Point.
Run directly using: python run.py
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("================================================================")
    print(" MetroCare General Hospital — Coimbatore, Tamil Nadu, India")
    print(" Outpatient Appointment Management System")
    print(" Server Active: http://127.0.0.1:5000")
    print(" ---------------------------------------------------------------")
    print(" Demo Logins (Pass: Admin@123 / Doctor@123 / Patient@123):")
    print(" • Admin:   admin@mediflow.com   (Dr. R. Senthil Kumar, Med Supdt)")
    print(" • Doctor:  sarah.jenkins@mediflow.com (Dr. S. Sundararajan, Cardio)")
    print(" • Patient: alex.rivera@example.com (K. Vignesh, Singanallur)")
    print("================================================================")
    app.run(host='127.0.0.1', port=5000, debug=True)
