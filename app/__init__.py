"""
MediFlow Flask Application Factory.
Initializes the Flask app, configures session security, registers blueprints,
and registers template helpers and error handlers.
"""

import os
from flask import Flask, render_template
from app.database import init_db

def create_app(test_config=None):
    """Factory creating and configuring the Flask application instance."""
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'mediflow-secure-clinical-key-2026-xyz'),
        TEMPLATES_AUTO_RELOAD=True
    )

    if test_config is not None:
        app.config.update(test_config)

    # Initialize SQLite database schema and sample data on startup
    with app.app_context():
        init_db(force_reseed=False)

    # Register Blueprints
    from app.main import main_bp
    from app.auth import auth_bp
    from app.patient import patient_bp
    from app.doctor import doctor_bp
    from app.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp)

    # Custom Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    # Context processor to inject common utility variables into templates
    @app.context_processor
    def inject_utilities():
        import datetime
        return dict(
            current_year=datetime.datetime.now().year,
            app_name="MediFlow"
        )

    return app

if __name__ == '__main__':
    application = create_app()
    application.run(host='127.0.0.1', port=5000, debug=True)
