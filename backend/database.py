import sqlite3
import os
from werkzeug.security import generate_password_hash

import shutil

# Vercel Serverless read-only filesystem handling
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "habitflow.db")

if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    DB_PATH = "/tmp/habitflow.db"
    # Copy pre-seeded database template to /tmp if not present
    if not os.path.exists(DB_PATH) and os.path.exists(DEFAULT_DB_PATH):
        try:
            shutil.copyfile(DEFAULT_DB_PATH, DB_PATH)
        except Exception as e:
            print(f"Error copying DB to /tmp: {e}")
else:
    DB_PATH = DEFAULT_DB_PATH

def ensure_tables_exist(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if not cursor.fetchone():
            print("[Database Notice] Tables missing, initializing database schema and seed data...")
            init_db_schema_and_seed(conn)
    except Exception as e:
        print(f"[Database Error] Table verification error: {e}")

def get_db():
    try:
        # If on Vercel and DB doesn't exist yet in /tmp, copy template if available
        if (os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV")) and not os.path.exists(DB_PATH):
            if os.path.exists(DEFAULT_DB_PATH):
                try:
                    shutil.copyfile(DEFAULT_DB_PATH, DB_PATH)
                except Exception as e:
                    print(f"Error copying DB template: {e}")
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        ensure_tables_exist(conn)
        return conn
    except Exception as e:
        print(f"[DB Connect Warning] Falling back to in-memory DB: {e}")
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        ensure_tables_exist(conn)
        return conn

def init_db_schema_and_seed(conn):
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        is_active INTEGER DEFAULT 1,
        is_verified INTEGER DEFAULT 0,
        verification_code TEXT,
        theme TEXT DEFAULT 'light',
        weekly_emails INTEGER DEFAULT 1,
        notifications INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Categories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        color TEXT DEFAULT '#4caf50',
        icon TEXT DEFAULT 'check'
    );
    """)

    # Tasks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL,
        color TEXT DEFAULT '#4caf50',
        icon TEXT DEFAULT 'circle',
        priority TEXT DEFAULT 'medium',
        is_active INTEGER DEFAULT 1,
        is_archived INTEGER DEFAULT 0,
        recurrence TEXT DEFAULT 'daily',
        recurrence_days TEXT,
        order_idx INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Completions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS completions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        completed INTEGER DEFAULT 1,
        UNIQUE(task_id, date),
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
    );
    """)

    # Announcements Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Reminders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        time TEXT NOT NULL,
        is_enabled INTEGER DEFAULT 1,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
    );
    """)

    # System Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT DEFAULT 'info',
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    seed_data(conn)

def init_db():
    conn = get_db()
    conn.close()

def log_event(level, message):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO system_logs (level, message) VALUES (?, ?);", (level, message))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging event: {e}")

def seed_data(conn):
    cursor = conn.cursor()

    # Seed categories
    categories = [
        ("Health & Wellness", "#2d5a27", "heart"),
        ("Fitness", "#4caf50", "running"),
        ("Personal Development", "#ff9800", "book"),
        ("Career & Work", "#2196f3", "briefcase"),
        ("Study & Learn", "#9c27b0", "graduation-cap"),
        ("Finance", "#009688", "wallet")
    ]
    for cat in categories:
        cursor.execute("""
        INSERT OR IGNORE INTO categories (name, color, icon) VALUES (?, ?, ?);
        """, cat)

    # Seed Admin User
    admin_email = "admin@habitflow.com"
    admin_password = "adminpassword"
    admin_hash = generate_password_hash(admin_password)
    cursor.execute("""
    INSERT OR IGNORE INTO users (name, email, password_hash, role, is_active, is_verified)
    VALUES (?, ?, ?, 'admin', 1, 1);
    """, ("System Administrator", admin_email, admin_hash))

    # Seed Demo User
    demo_email = "demo@habitflow.com"
    demo_password = "demopassword"
    demo_hash = generate_password_hash(demo_password)
    cursor.execute("""
    INSERT OR IGNORE INTO users (name, email, password_hash, role, is_active, is_verified)
    VALUES (?, ?, ?, 'user', 1, 1);
    """, ("Demo User", demo_email, demo_hash))

    # Get Demo User ID
    cursor.execute("SELECT id FROM users WHERE email = ?;", (demo_email,))
    user_row = cursor.fetchone()
    if user_row:
        user_id = user_row[0]

        # Seed Tasks for Demo User
        default_tasks = [
            ("Wake up before 6 AM", "Start the day early and productively", "Health & Wellness", "#2d5a27", "sun", "high", "daily", 0),
            ("Exercise 30 minutes", "Keep fit with running, stretching or strength training", "Fitness", "#4caf50", "dumbbell", "medium", "daily", 1),
            ("No Porn", "Stay focused and clear-minded", "Personal Development", "#d32f2f", "ban", "high", "daily", 2),
            ("Phone usage less than 3 hours", "Limit distractions and screen time", "Personal Development", "#ff9800", "mobile-alt", "medium", "daily", 3),
            ("BCS Study 30 minutes", "Read BCS exam preparation materials", "Study & Learn", "#9c27b0", "book-reader", "high", "daily", 4),
            ("English Practice 30 minutes", "Practice speaking, listening or vocabulary", "Study & Learn", "#2196f3", "language", "low", "daily", 5)
        ]

        # Add tasks if not already exist
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?;", (user_id,))
        task_count = cursor.fetchone()[0]
        if task_count == 0:
            for task in default_tasks:
                cursor.execute("""
                INSERT INTO tasks (name, description, category, color, icon, priority, recurrence, order_idx, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, task + (user_id,))
            
            # Fetch inserted task IDs
            cursor.execute("SELECT id, name FROM tasks WHERE user_id = ?;", (user_id,))
            inserted_tasks = cursor.fetchall()
            
            # Let's seed completions history to create a dynamic dashboard
            # We want to seed completions for the last 10 days, but simulate a mix of success and failure.
            import datetime
            today = datetime.date.today()
            
            # Tasks:
            # Wake up before 6 AM: 8 completed, 2 missed
            # Exercise 30 minutes: 7 completed
            # No Porn: 9 completed
            # Phone usage: 6 completed
            # BCS Study: 8 completed
            # English practice: 5 completed
            
            completion_patterns = {
                "Wake up before 6 AM": [0, 1, 2, 3, 4, 5, 7, 8], # offset in days from today (subtracting)
                "Exercise 30 minutes": [0, 1, 2, 4, 5, 6, 9],
                "No Porn": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                "Phone usage less than 3 hours": [0, 2, 3, 5, 6, 8],
                "BCS Study 30 minutes": [0, 1, 2, 3, 5, 6, 7, 9],
                "English Practice 30 minutes": [0, 1, 3, 5, 7]
            }

            for t_id, t_name in inserted_tasks:
                if t_name in completion_patterns:
                    offsets = completion_patterns[t_name]
                    for offset in offsets:
                        comp_date = (today - datetime.timedelta(days=offset)).isoformat()
                        cursor.execute("""
                        INSERT OR IGNORE INTO completions (task_id, date, completed)
                        VALUES (?, ?, 1);
                        """, (t_id, comp_date))

            # Add seed announcements
            cursor.execute("SELECT COUNT(*) FROM announcements;")
            ann_count = cursor.fetchone()[0]
            if ann_count == 0:
                cursor.execute("""
                INSERT INTO announcements (title, content)
                VALUES (?, ?);
                """, ("Welcome to HabitFlow!", "We are excited to help you build healthy habits and tracks your daily goals. Take a look around and customize your themes!"))
                cursor.execute("""
                INSERT INTO announcements (title, content)
                VALUES (?, ?);
                """, ("New Feature: Heatmap Calendar", "Now you can track your productivity with our new interactive calendar heatmap on the dashboard."))

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
