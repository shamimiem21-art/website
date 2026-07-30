import os
import sys
import time
import webbrowser
import threading

# Add backend directory to path to allow importing app
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.append(backend_dir)

from app import app
from database import DB_PATH

def open_browser():
    # Wait for Flask to boot
    time.sleep(2)
    url = "http://127.0.0.1:5000"
    print(f"\n[HabitFlow Bootloader] Launching default browser at {url}...")
    webbrowser.open(url)

if __name__ == "__main__":
    print("=" * 60)
    print("      Welcome to HabitFlow Habit Tracker Startup")
    print("=" * 60)
    print(f"Database File: {DB_PATH}")
    print("Starting Flask Backend Service on port 5000...")
    
    # Launch browser opening logic on separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Flask server
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    except KeyboardInterrupt:
        print("\nHabitFlow server stopped. Keep Flowing!")
