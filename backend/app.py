import os
from flask import Flask, send_from_directory, jsonify, request
from dotenv import load_dotenv

# Load env variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Import DB and blueprints
from database import init_db, get_db, log_event
from auth import auth_bp, login_required
from tasks import tasks_bp
from reports import reports_bp
from admin import admin_bp

app = Flask(__name__, static_folder="../frontend")

# Configure app secret
app.secret_key = os.environ.get("SECRET_KEY", "habitflow-app-secret-3456789")

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(tasks_bp, url_prefix="/api/tasks")
app.register_blueprint(reports_bp, url_prefix="/api/reports")
app.register_blueprint(admin_bp, url_prefix="/api/admin")

@app.before_request
def handle_options_preflight():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response, 200

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

# Initialize Database on boot
with app.app_context():
    try:
        init_db()
        log_event("info", "Application booted and database verified.")
    except Exception as e:
        print(f"Database init notice: {e}")
    
    # Automated background weekly email reporter thread (Only for non-serverless environments)
    if not os.environ.get("VERCEL") and not os.environ.get("VERCEL_ENV"):
        import threading
        import time
        import datetime
        from database import get_db
        from email_service import send_email
        
        def background_weekly_reporter():
            time.sleep(10)
            while True:
                try:
                    today = datetime.date.today()
                    if today.weekday() == 6:
                        conn = get_db()
                        cursor = conn.cursor()
                        cursor.execute("SELECT id, name, email FROM users WHERE role = 'user' AND is_active = 1 AND weekly_emails = 1;")
                        users = [dict(row) for row in cursor.fetchall()]
                        
                        for u in users:
                            user_id = u["id"]
                            email = u["email"]
                            name = u["name"]
                            
                            cursor.execute("""
                                SELECT COUNT(*) FROM system_logs 
                                WHERE level = 'info' AND message LIKE ? AND created_at > datetime('now', '-6 days');
                            """, (f"Weekly report email sent to: {email}%",))
                            already_sent = cursor.fetchone()[0]
                            
                            if already_sent == 0:
                                from reports import generate_weekly_report_data
                                report_data = generate_weekly_report_data(user_id)
                                suggestions_html = "".join([f"<li style='margin-bottom: 8px; color: #333;'>{s}</li>" for s in report_data["suggestions"]])
                                report_html = f"""
                                <div style="background-color: #f4f8f4; border: 1px solid #d8ebd4; padding: 20px; border-radius: 8px; margin: 15px 0;">
                                    <h3>Weekly Summary</h3>
                                    <p>Completion Rate: {report_data["weekly_pct"]}%</p>
                                    <ul>{suggestions_html}</ul>
                                </div>
                                """
                                success = send_email(email, "Weekly Summary - HabitFlow 🌿", report_html, "weekly")
                                if success:
                                    cursor.execute("INSERT INTO system_logs (level, message) VALUES ('info', ?);", (f"Weekly report email sent to: {email}",))
                                    conn.commit()
                        conn.close()
                except Exception as e:
                    print(f"[Weekly Reporter Error] {e}")
                time.sleep(43200)

        threading.Thread(target=background_weekly_reporter, daemon=True).start()

# User profile update endpoint
@app.route("/api/user/profile", methods=["PUT"])
@login_required
def update_profile():
    user_id = request.user["id"]
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    theme = data.get("theme", "light").strip()
    weekly_emails = data.get("weekly_emails")
    notifications = data.get("notifications")
    
    conn = get_db()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if name:
        updates.append("name = ?")
        params.append(name)
    if theme in ["light", "dark"]:
        updates.append("theme = ?")
        params.append(theme)
    if weekly_emails is not None:
        updates.append("weekly_emails = ?")
        params.append(int(weekly_emails))
    if notifications is not None:
        updates.append("notifications = ?")
        params.append(int(notifications))
        
    if not updates:
        conn.close()
        return jsonify({"error": "No updates provided"}), 400
        
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?;"
    params.append(user_id)
    
    try:
        cursor.execute(query, params)
        conn.commit()
        log_event("info", f"Profile updated for user_id={user_id}")
        return jsonify({"message": "Profile updated successfully"})
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

# Reminders Endpoints
@app.route("/api/reminders", methods=["GET"])
@login_required
def get_reminders():
    user_id = request.user["id"]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.task_id, r.time, r.is_enabled, t.name as task_name
        FROM reminders r
        JOIN tasks t ON r.task_id = t.id
        WHERE t.user_id = ?;
    """, (user_id,))
    reminders = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"reminders": reminders})

@app.route("/api/reminders", methods=["POST"])
@login_required
def add_reminder():
    user_id = request.user["id"]
    data = request.get_json() or {}
    task_id = data.get("task_id")
    time_str = data.get("time", "").strip() # HH:MM
    is_enabled = data.get("is_enabled", 1)
    
    if not task_id or not time_str:
        return jsonify({"error": "task_id and time (HH:MM) are required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    # Check task ownership
    cursor.execute("SELECT id FROM tasks WHERE id = ? AND user_id = ?;", (task_id, user_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Task not found"}), 404
        
    try:
        # Delete existing reminders for this task to keep it simple (one reminder per task)
        cursor.execute("DELETE FROM reminders WHERE task_id = ?;", (task_id,))
        
        cursor.execute("""
            INSERT INTO reminders (task_id, time, is_enabled)
            VALUES (?, ?, ?);
        """, (task_id, time_str, int(is_enabled)))
        conn.commit()
        return jsonify({"message": "Reminder set successfully"}), 201
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@app.route("/api/reminders/<int:reminder_id>", methods=["DELETE"])
@login_required
def delete_reminder(reminder_id):
    user_id = request.user["id"]
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify ownership through task joining
    cursor.execute("""
        SELECT r.id FROM reminders r
        JOIN tasks t ON r.task_id = t.id
        WHERE r.id = ? AND t.user_id = ?;
    """, (reminder_id, user_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Reminder not found"}), 404
        
    try:
        cursor.execute("DELETE FROM reminders WHERE id = ?;", (reminder_id,))
        conn.commit()
        return jsonify({"message": "Reminder deleted successfully"})
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

# SPA Routing: Serve index.html for all non-API paths
@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def serve_spa(path):
    if request.method == "OPTIONS":
        return "", 200
    if path.startswith("api/") or path.startswith("api"):
        return jsonify({"error": "API endpoint not found"}), 404
    # Check if path looks like a static asset, serve it
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        # Otherwise serve index.html (fallback router handles the hashing)
        return send_from_directory(app.static_folder, "index.html")

@app.errorhandler(405)
def handle_405(err):
    return jsonify({"error": "Method Not Allowed"}), 200

@app.errorhandler(500)
def handle_500(err):
    return jsonify({"error": f"Internal Server Error: {str(err)}"}), 500

@app.errorhandler(Exception)
def handle_exception(err):
    return jsonify({"error": f"Application Error: {str(err)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Run server on all interfaces (localhost & local network IP)
    app.run(host="0.0.0.0", port=port, debug=True)
