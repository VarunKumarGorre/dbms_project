"""
RPGMS Application Runner
File: run.py
Author: Antigravity AI
"""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="127.0.0.1", port=port, debug=False)
