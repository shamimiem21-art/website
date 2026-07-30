import json
import os
import uuid
from flask import Blueprint, jsonify, request
from auth import admin_required
from database import get_db, log_event
from werkzeug.security import generate_password_hash

admin_bp = Blueprint("admin", __name__)

FLAGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feature_flags.json")

def get_feature_flags():
    default_flags = {
        "pomodoro": {"enabled": True, "name": "Pomodoro Timer"},
        "expenses": {"enabled": False, "name": "Expense Tracker"},
        "goals": {"enabled": True, "name": "Goal Tracker"},
        "mood": {"enabled": True, "name": "Mood Tracker"},
        "journal": {"enabled": False, "name": "Daily Journal"},
        "fitness": {"enabled": False, "name": "Fitness Tracker"},
        "ai_coach": {"enabled": False, "name": "AI Habits Coach"}
    }
    
    if not os.path.exists(FLAGS_PATH):
        with open(FLAGS_PATH, "w") as f:
            json.dump(default_flags, f, indent=4)
        return default_flags
        
    try:
        with open(FLAGS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return default_flags

def save_feature_flags(flags):
    with open(FLAGS_PATH, "w") as f:
        json.dump(flags, f, indent=4)

@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, role, is_active, is_verified, created_at,
        (SELECT COUNT(*) FROM tasks WHERE user_id = users.id) as task_count,
        (SELECT COUNT(*) FROM completions c JOIN tasks t ON c.task_id = t.id WHERE t.user_id = users.id) as completion_count
        FROM users
        ORDER BY created_at DESC;
    """)
    users = [dict(u) for u in cursor.fetchall()]
    conn.close()
    return jsonify({"users": users})

@admin_bp.route("/users/<int:user_id>/suspend", methods=["POST"])
@admin_required
def suspend_user(user_id):
    if user_id == request.user["id"]:
        return jsonify({"error": "You cannot suspend your own admin account"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?;", (user_id,))
        conn.commit()
        log_event("warning", f"Admin suspended user_id={user_id}")
        return jsonify({"message": "User suspended successfully"})
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@admin_bp.route("/users/<int:user_id>/unsuspend", methods=["POST"])
@admin_required
def unsuspend_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_active = 1 WHERE id = ?;", (user_id,))
        conn.commit()
        log_event("info", f"Admin unsuspended user_id={user_id}")
        return jsonify({"message": "User unsuspended successfully"})
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def reset_user_password(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if target is not current admin (admins shouldn't force-reset self password without confirmation)
    temp_password = str(uuid.uuid4().hex[:8]) # e.g. a secure 8-character string
    password_hash = generate_password_hash(temp_password)
    
    try:
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?;", (password_hash, user_id))
        conn.commit()
        log_event("info", f"Admin force-reset password for user_id={user_id}")
        return jsonify({"message": "Password reset successfully", "new_password": temp_password})
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    if user_id == request.user["id"]:
        return jsonify({"error": "You cannot delete your own admin account"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
        conn.commit()
        log_event("warning", f"Admin deleted user_id={user_id}")
        return jsonify({"message": "User deleted successfully"})
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@admin_bp.route("/stats", methods=["GET"])
@admin_required
def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user';")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tasks;")
    total_habits = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM completions;")
    total_completions = cursor.fetchone()[0]
    
    # Active users count today
    import datetime
    today_str = datetime.date.today().isoformat()
    cursor.execute("""
        SELECT COUNT(DISTINCT t.user_id) 
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE c.date = ?;
    """, (today_str,))
    active_today = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "stats": {
            "total_users": total_users,
            "total_habits": total_habits,
            "total_completions": total_completions,
            "active_today": active_today
        }
    })

@admin_bp.route("/logs", methods=["GET"])
@admin_required
def get_logs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM system_logs ORDER BY created_at DESC LIMIT 100;")
    logs = [dict(l) for l in cursor.fetchall()]
    conn.close()
    return jsonify({"logs": logs})

@admin_bp.route("/categories", methods=["GET"])
@admin_required
def get_categories():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY id ASC;")
    cats = [dict(c) for c in cursor.fetchall()]
    conn.close()
    return jsonify({"categories": cats})

@admin_bp.route("/categories", methods=["POST"])
@admin_required
def add_category():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    color = data.get("color", "#4caf50").strip()
    icon = data.get("icon", "circle").strip()
    
    if not name:
        return jsonify({"error": "Category name is required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name, color, icon) VALUES (?, ?, ?);", (name, color, icon))
        conn.commit()
        return jsonify({"message": "Category added successfully"}), 201
    except Exception as e:
        return jsonify({"error": "Category already exists or database error"}), 409
    finally:
        conn.close()

@admin_bp.route("/categories/<int:cat_id>", methods=["DELETE"])
@admin_required
def delete_category(cat_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM categories WHERE id = ?;", (cat_id,))
        conn.commit()
        return jsonify({"message": "Category deleted successfully"})
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@admin_bp.route("/announcements", methods=["POST"])
@admin_required
def create_announcement():
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    
    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO announcements (title, content) VALUES (?, ?);", (title, content))
        conn.commit()
        log_event("info", f"Admin pushed announcement: '{title}'")
        return jsonify({"message": "Announcement created successfully"}), 201
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@admin_bp.route("/announcements", methods=["GET"])
def get_announcements():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM announcements ORDER BY created_at DESC;")
    anns = [dict(a) for a in cursor.fetchall()]
    conn.close()
    return jsonify({"announcements": anns})

@admin_bp.route("/announcements/<int:ann_id>", methods=["DELETE"])
@admin_required
def delete_announcement(ann_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM announcements WHERE id = ?;", (ann_id,))
        conn.commit()
        return jsonify({"message": "Announcement deleted successfully"})
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@admin_bp.route("/feature-flags", methods=["GET"])
def get_flags_route():
    flags = get_feature_flags()
    return jsonify({"feature_flags": flags})

@admin_bp.route("/feature-flags", methods=["POST"])
@admin_required
def toggle_flag():
    data = request.get_json() or {}
    flag_key = data.get("key", "").strip()
    enabled = data.get("enabled")
    
    if not flag_key or enabled is None:
        return jsonify({"error": "Flag key and enabled status are required"}), 400
        
    flags = get_feature_flags()
    if flag_key not in flags:
        return jsonify({"error": "Flag not found"}), 404
        
    flags[flag_key]["enabled"] = bool(enabled)
    save_feature_flags(flags)
    log_event("info", f"Admin toggled feature flag '{flag_key}' to {enabled}")
    return jsonify({"message": f"Feature '{flag_key}' has been updated", "feature_flags": flags})
