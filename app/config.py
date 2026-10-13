"""
RPGMS Application Configuration
File: app/config.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if os.getenv("FLASK_ENV") == "testing" or os.getenv("TESTING") == "1":
            SECRET_KEY = "ephemeral-test-secret-key-32-chars-long"
        else:
            raise RuntimeError("CRITICAL: SECRET_KEY environment variable is required and must not be empty.")

    APP_ENV = os.getenv("APP_ENV", "production")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # MySQL Configuration
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_NAME = os.getenv("DB_NAME", "rpgms")
    DB_USER = os.getenv("DB_USER", "rpgms_app")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "rpgms_app_pass")

    # Pool settings
    DB_POOL_NAME = "rpgms_pool"
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))

    # Cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = 3600 * 8  # 8 hours

class TestConfig(Config):
    TESTING = True
    DB_NAME = os.getenv("TEST_DB_NAME", "rpgms_test")
    DB_USER = os.getenv("DB_TEST_USER", os.getenv("DB_USER", "rpgms_test_user"))
    DB_PASSWORD = os.getenv("DB_TEST_PASSWORD", os.getenv("DB_PASSWORD", "rpgms_test_pass"))
    WTF_CSRF_ENABLED = False
