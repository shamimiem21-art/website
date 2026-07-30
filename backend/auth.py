import jwt
import datetime
import uuid
import os
from flask import Blueprint, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, log_event
from email_service import send_verification_email, send_reset_password_email

auth_bp = Blueprint("auth", __name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "habitflow-super-secret-key-123456")
COOKIE_NAME = "habitflow_token"

def generate_token(user_id, role, name):
    payload = {
        "user_id": user_id,
        "role": role,
        "name": name,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_current_user():
    # Check Cookie first
    token = request.cookies.get(COOKIE_NAME)
    
    # Check Authorization header if no cookie
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        return None
        
    payload = decode_token(token)
    if not payload:
        return None
        
    # Check if user exists in database and is active
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, is_active, is_verified, theme, weekly_emails, notifications FROM users WHERE id = ?;", (payload["user_id"],))
    user = cursor.fetchone()
    conn.close()
    
    if not user or user["is_active"] == 0:
        return None
        
    return dict(user)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        request.user = user
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        if user["role"] != "admin":
            return jsonify({"error": "Admin access required"}), 403
        request.user = user
        return f(*args, **kwargs)
    return decorated

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400
        
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = get_db()
    cursor = conn.cursor()
    
    # Check if email exists
    cursor.execute("SELECT id FROM users WHERE email = ?;", (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Email is already registered"}), 409
        
    # Hash password
    password_hash = generate_password_hash(password)
    
    try:
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, is_active, is_verified)
        VALUES (?, ?, ?, 'user', 1, 1);
        """, (name, email, password_hash))
        conn.commit()
        
        user_id = cursor.lastrowid
        log_event("info", f"User registered (auto-verified): {email}")
        
        # Generate token and login automatically
        token = generate_token(user_id, 'user', name)
        
        resp = make_response(jsonify({
            "message": "Registration successful! You have been logged in automatically.",
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "role": "user"
            }
        }))
        resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="Lax", max_age=7*24*60*60)
        return resp
    except Exception as e:
        log_event("error", f"Registration error for {email}: {str(e)}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    code = data.get("code", "").strip().upper()
    
    if not email or not code:
        return jsonify({"error": "Email and verification code are required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, verification_code, is_verified FROM users WHERE email = ?;", (email,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404
        
    if user["is_verified"] == 1:
        conn.close()
        return jsonify({"message": "Email is already verified"}), 200
        
    if user["verification_code"] != code:
        conn.close()
        return jsonify({"error": "Invalid verification code"}), 400
        
    try:
        cursor.execute("UPDATE users SET is_verified = 1, verification_code = NULL WHERE id = ?;", (user["id"],))
        conn.commit()
        log_event("info", f"User email verified: {email}")
        return jsonify({"message": "Email verified successfully. You can now log in."}), 200
    except Exception as e:
        log_event("error", f"Verification error for {email}: {str(e)}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, password_hash, role, is_active, is_verified FROM users WHERE email = ? AND role != 'admin';", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401
        
    if user["is_active"] == 0:
        return jsonify({"error": "Your account has been suspended. Please contact admin."}), 403
        
    token = generate_token(user["id"], user["role"], user["name"])
    
    resp = make_response(jsonify({
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }))
    # Set JWT as HTTP-only cookie
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="Lax", max_age=7*24*60*60)
    log_event("info", f"User logged in: {email}")
    return resp

@auth_bp.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, password_hash, role, is_active FROM users WHERE email = ? AND role = 'admin';", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid admin credentials"}), 401
        
    if user["is_active"] == 0:
        return jsonify({"error": "Admin account suspended"}), 403
        
    token = generate_token(user["id"], user["role"], user["name"])
    
    resp = make_response(jsonify({
        "message": "Admin login successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }))
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="Lax", max_age=7*24*60*60)
    log_event("info", f"Admin logged in: {email}")
    return resp

@auth_bp.route("/logout", methods=["POST"])
def logout():
    resp = make_response(jsonify({"message": "Logout successful"}))
    resp.delete_cookie(COOKIE_NAME)
    return resp

@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify({"user": request.user})

@auth_bp.route("/reset-password-request", methods=["POST"])
def reset_password_request():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users WHERE email = ?;", (email,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        # To avoid email enumeration, we return success even if user not found,
        # but let's return success with a generic message.
        return jsonify({"message": "If the email exists, a password reset code has been sent."}), 200
        
    verification_code = str(uuid.uuid4().hex[:6]).upper()
    try:
        cursor.execute("UPDATE users SET verification_code = ? WHERE id = ?;", (verification_code, user["id"]))
        conn.commit()
        
        send_reset_password_email(email, user["name"], verification_code)
        log_event("info", f"Password reset requested for: {email}")
        return jsonify({"message": "Password reset code sent to your email."}), 200
    except Exception as e:
        log_event("error", f"Reset password request error for {email}: {str(e)}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    code = data.get("code", "").strip().upper()
    new_password = data.get("password", "")
    
    if not email or not code or not new_password:
        return jsonify({"error": "Email, verification code, and new password are required"}), 400
        
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, verification_code FROM users WHERE email = ?;", (email,))
    user = cursor.fetchone()
    
    if not user or user["verification_code"] != code:
        conn.close()
        return jsonify({"error": "Invalid email or verification code"}), 400
        
    password_hash = generate_password_hash(new_password)
    try:
        cursor.execute("UPDATE users SET password_hash = ?, verification_code = NULL, is_verified = 1 WHERE id = ?;", (password_hash, user["id"]))
        conn.commit()
        log_event("info", f"Password reset completed for: {email}")
        return jsonify({"message": "Password reset successfully. You can now log in."}), 200
    except Exception as e:
        log_event("error", f"Reset password error for {email}: {str(e)}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json() or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    
    if not old_password or not new_password:
        return jsonify({"error": "Old and new passwords are required"}), 400
        
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE id = ?;", (request.user["id"],))
    user = cursor.fetchone()
    
    if not user or not check_password_hash(user["password_hash"], old_password):
        conn.close()
        return jsonify({"error": "Incorrect current password"}), 400
        
    password_hash = generate_password_hash(new_password)
    try:
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (password_hash, request.user["id"]))
        conn.commit()
        log_event("info", f"Password changed for user id: {request.user['id']}")
        return jsonify({"message": "Password changed successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@auth_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    data = request.get_json() or {}
    password = data.get("password", "")
    
    if not password:
        return jsonify({"error": "Password is required to delete your account"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE id = ?;", (request.user["id"],))
    user = cursor.fetchone()
    
    if not user or not check_password_hash(user["password_hash"], password):
        conn.close()
        return jsonify({"error": "Incorrect password"}), 400
        
    try:
        # Delete user (completions and tasks will be deleted by CASCADE foreign keys)
        cursor.execute("DELETE FROM users WHERE id = ?;", (request.user["id"],))
        conn.commit()
        log_event("info", f"User account deleted: user_id={request.user['id']}, email={request.user['email']}")
        
        resp = make_response(jsonify({"message": "Account deleted successfully"}))
        resp.delete_cookie(COOKIE_NAME)
        return resp
    except Exception as e:
        log_event("error", f"Delete account error for user_id={request.user['id']}: {str(e)}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()
