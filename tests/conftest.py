"""
RPGMS Pytest Configuration and Test Fixtures
File: tests/conftest.py
Author: Antigravity AI

Sets up the isolated test database (rpgms_test), test client sessions,
and authenticated clients across all 4 system roles.
"""

import subprocess
import os
import sys
from pathlib import Path
import pytest
import mysql.connector

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app.config import TestConfig
from app.db import init_db_pool, _connection_pool

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Rebuilds the separate test database rpgms_test before the test session begins.
    Strictly target-checks to ensure only rpgms_test is modified.
    """
    setup_script = ROOT_DIR / "db" / "setup_db.py"
    cmd = [
        sys.executable,
        str(setup_script),
        "--database", "rpgms_test",
        "--reset",
        "--seed",
        "--confirm-reset", "rpgms_test"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to reset rpgms_test:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
    yield

@pytest.fixture
def test_db():
    """Provides a direct connection to rpgms_test using test credentials."""
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        database="rpgms_test",
        user=os.getenv("DB_TEST_USER", "rpgms_test_user"),
        password=os.getenv("DB_TEST_PASSWORD", "rpgms_test_pass"),
        autocommit=True
    )
    yield conn
    conn.close()

@pytest.fixture
def app():
    """Creates a Flask application configured for testing on rpgms_test."""
    application = create_app(TestConfig)
    application.config["WTF_CSRF_ENABLED"] = False
    with application.app_context():
        init_db_pool(application)
        yield application

@pytest.fixture
def client(app):
    """Unauthenticated Flask test client."""
    return app.test_client()

@pytest.fixture
def admin_client(app):
    """Authenticated client for user 'admin' (Role: ADMIN)."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["role"] = "ADMIN"
        sess["display_name"] = "System Administrator"
        sess["researcher_id"] = None
    return c

@pytest.fixture
def officer_client(app):
    """Authenticated client for user 'officer' (Role: RESEARCH_OFFICER)."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["user_id"] = 2
        sess["username"] = "officer"
        sess["role"] = "RESEARCH_OFFICER"
        sess["display_name"] = "Research Officer"
        sess["researcher_id"] = None
    return c

@pytest.fixture
def pi_client(app):
    """Authenticated client for user 'pi_rao' (Role: PI, Researcher: Dr. Aravind Rao)."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["user_id"] = 3
        sess["username"] = "pi_rao"
        sess["role"] = "PI"
        sess["display_name"] = "Prof. Aravind Rao"
        sess["researcher_id"] = 1
    return c

@pytest.fixture
def viewer_client(app):
    """Authenticated client for user 'viewer' (Role: VIEWER)."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["user_id"] = 6
        sess["username"] = "viewer"
        sess["role"] = "VIEWER"
        sess["display_name"] = "Institutional Auditor"
        sess["researcher_id"] = None
    return c
