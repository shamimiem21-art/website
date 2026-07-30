import sys
import os

# Set VERCEL environment flag
os.environ["VERCEL"] = "1"

# Ensure backend directory is in Python path for Vercel Serverless Function
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from app import app
    app = app
except Exception as e:
    from flask import Flask, jsonify
    app = Flask(__name__)
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path):
        return jsonify({"error": "Vercel serverless startup error", "details": str(e)}), 500
