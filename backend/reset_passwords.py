import sqlite3
from werkzeug.security import generate_password_hash
import os

DB_PATH = r"C:\Users\Acer\.gemini\antigravity\scratch\habitflow\backend\habitflow.db"

def reset_all_passwords():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Hash for '123456'
    pwd_123456_hash = generate_password_hash("123456")
    # Hash for 'adminpassword'
    admin_pwd_hash = generate_password_hash("adminpassword")
    # Hash for 'demopassword'
    demo_pwd_hash = generate_password_hash("demopassword")
    
    # Update admin
    cursor.execute("UPDATE users SET password_hash = ? WHERE email = 'admin@habitflow.com';", (admin_pwd_hash,))
    
    # Update demo
    cursor.execute("UPDATE users SET password_hash = ? WHERE email = 'demo@habitflow.com';", (demo_pwd_hash,))
    
    # Update all other users to accept '123456' or 'demopassword'
    cursor.execute("UPDATE users SET password_hash = ? WHERE role = 'user' AND email != 'demo@habitflow.com';", (pwd_123456_hash,))
    
    conn.commit()
    conn.close()
    print("All user passwords successfully reset and updated!")

if __name__ == "__main__":
    reset_all_passwords()
