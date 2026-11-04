"""
Main blueprint for public-facing pages:
Homepage, Doctors directory with search & department filters, Department overview, About & Contact.
"""

from flask import Blueprint, render_template, request
from app.database import get_db_connection

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Polished clinical landing page with stats, departments, and featured doctors."""
    conn = get_db_connection()
    departments = conn.execute("SELECT * FROM departments LIMIT 6").fetchall()
    
    # Fetch top doctors
    doctors = conn.execute("""
        SELECT d.*, u.full_name, u.email, u.phone, dept.name as department_name, dept.icon as dept_icon
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        JOIN departments dept ON d.department_id = dept.id
        ORDER BY d.experience_years DESC
        LIMIT 4
    """).fetchall()

    # Metrics for hero counter
    stats = {
        'doctors_count': conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0],
        'departments_count': conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0],
        'patients_count': conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0],
        'appointments_count': conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
    }
    conn.close()

    return render_template('index.html', departments=departments, doctors=doctors, stats=stats)

@main_bp.route('/doctors')
def doctors():
    """Doctors listing with dynamic filtering by specialty/department and keyword search."""
    search_query = request.args.get('search', '').strip()
    dept_id = request.args.get('department', '').strip()

    conn = get_db_connection()
    departments = conn.execute("SELECT * FROM departments ORDER BY name").fetchall()

    query = """
        SELECT d.*, u.full_name, u.email, u.phone, dept.name as department_name, dept.icon as dept_icon
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        JOIN departments dept ON d.department_id = dept.id
        WHERE 1=1
    """
    params = []

    if search_query:
        query += " AND (u.full_name LIKE ? OR d.specialization LIKE ? OR d.qualification LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term])

    if dept_id and dept_id.isdigit():
        query += " AND d.department_id = ?"
        params.append(int(dept_id))

    query += " ORDER BY u.full_name ASC"
    doctor_list = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('doctors.html', doctors=doctor_list, departments=departments,
                           search_query=search_query, selected_dept=dept_id)

@main_bp.route('/departments')
def departments():
    """Department directory with descriptions and doctor counts."""
    conn = get_db_connection()
    depts = conn.execute("""
        SELECT dept.*, COUNT(d.id) as doctor_count
        FROM departments dept
        LEFT JOIN doctors d ON dept.id = d.department_id
        GROUP BY dept.id
        ORDER BY dept.name ASC
    """).fetchall()
    conn.close()
    return render_template('departments.html', departments=depts)

@main_bp.route('/about')
def about():
    """About MediFlow hospital, accreditation, mission, and hospital leadership."""
    return render_template('about.html')
