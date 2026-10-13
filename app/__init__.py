"""
RPGMS Flask Application Factory
File: app/__init__.py
Author: Antigravity AI
"""

from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from app.config import Config
from app.db import init_db_pool
from app.auth import get_current_user
from app.utils import (
    format_inr, format_inr_compact, format_pct,
    format_date_short, format_date_rel, get_initials, get_avatar_color
)

csrf = CSRFProtect()

def create_app(config_class=Config) -> Flask:
    """Creates and configures the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Database Pool Initialization
    init_db_pool(app)

    # CSRF Protection
    csrf.init_app(app)

    # Jinja2 Template Filters
    app.jinja_env.filters["inr"] = format_inr
    app.jinja_env.filters["inr_compact"] = format_inr_compact
    app.jinja_env.filters["pct"] = format_pct
    app.jinja_env.filters["date_short"] = format_date_short
    app.jinja_env.filters["date_rel"] = format_date_rel
    app.jinja_env.filters["initials"] = get_initials
    app.jinja_env.filters["avatar_color"] = get_avatar_color

    # Global Context Processor
    @app.context_processor
    def inject_user():
        return {
            "current_user": get_current_user()
        }

    # Register Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.projects import projects_bp
    from app.blueprints.investigators import investigators_bp
    from app.blueprints.grants import grants_bp
    from app.blueprints.milestones import milestones_bp
    from app.blueprints.expenditure import expenditure_bp
    from app.blueprints.publications import publications_bp
    from app.blueprints.patents import patents_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(investigators_bp)
    app.register_blueprint(grants_bp)
    app.register_blueprint(milestones_bp)
    app.register_blueprint(expenditure_bp)
    app.register_blueprint(publications_bp)
    app.register_blueprint(patents_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    return app
