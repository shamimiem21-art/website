import sys
import os

# Ensure backend directory is in Python path for Vercel Serverless Function
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import app

# Export WSGI application for Vercel @vercel/python builder
app = app
