import datetime
from flask import Blueprint, request, jsonify
from auth import login_required
from database import get_db, log_event

tasks_bp = Blueprint("tasks", __name__)

def is_task_scheduled_for_date(task, check_date):
    # check_date is a datetime.date object
    # Check if task was created after check_date
    created_at = task["created_at"]
    try:
        created_date = datetime.datetime.strptime(created_at.split(" ")[0], "%Y-%m-%d").date()
        if created_date > check_date:
            return False
    except Exception:
        pass

    if task["is_active"] == 0:
        return False
        
    recurrence = task["recurrence"]
    if recurrence == "daily":
        return True
        
    if recurrence == "weekly":
        # check recurrence_days (comma-separated days of week, e.g. "Mon,Wed,Fri")
        days = task["recurrence_days"]
        if not days:
            return True
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        check_day_name = day_names[check_date.weekday()] # check_date.weekday() is 0=Mon, 6=Sun
        active_days = [d.strip() for d in days.split(",")]
        return check_day_name in active_days
        
    return True

@tasks_bp.route("", methods=["GET"])
@login_required
def get_tasks():
    user_id = request.user["id"]
    date_str = request.args.get("date") # YYYY-MM-DD
    category = request.args.get("category")
    priority = request.args.get("priority")
    archived = request.args.get("archived", "0") # Default to active, non-archived
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Query tasks
    query = "SELECT * FROM tasks WHERE user_id = ? AND is_archived = ? "
    params = [user_id, int(archived)]
    
    if category:
        query += "AND category = ? "
        params.append(category)
    if priority:
        query += "AND priority = ? "
        params.append(priority)
        
    query += "ORDER BY order_idx ASC, id ASC"
    
    cursor.execute(query, params)
    tasks = [dict(t) for t in cursor.fetchall()]
    
    # If date is provided, filter tasks scheduled for this date and fetch completion status
    if date_str:
        try:
            check_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
            
        # Get completions for this date
        cursor.execute("""
            SELECT task_id, completed FROM completions 
            WHERE date = ? AND task_id IN (SELECT id FROM tasks WHERE user_id = ?)
        """, (date_str, user_id))
        completions = {row["task_id"]: row["completed"] for row in cursor.fetchall()}
        
        filtered_tasks = []
        for t in tasks:
            # Check if active on this date
            if is_task_scheduled_for_date(t, check_date):
                t["completed"] = completions.get(t["id"], 0)
                filtered_tasks.append(t)
            elif t["is_archived"] == 1:
                # Still show archived tasks in search if requested
                t["completed"] = completions.get(t["id"], 0)
                filtered_tasks.append(t)
        tasks = filtered_tasks
    else:
        # Just check completions for today
        today_str = datetime.date.today().isoformat()
        cursor.execute("""
            SELECT task_id FROM completions 
            WHERE date = ? AND task_id IN (SELECT id FROM tasks WHERE user_id = ?)
        """, (today_str, user_id))
        completed_ids = {row["task_id"] for row in cursor.fetchall()}
        for t in tasks:
            t["completed"] = 1 if t["id"] in completed_ids else 0
            
    conn.close()
    return jsonify({"tasks": tasks})

@tasks_bp.route("", methods=["POST"])
@login_required
def create_task():
    user_id = request.user["id"]
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    category = data.get("category", "General").strip()
    color = data.get("color", "#4caf50").strip()
    icon = data.get("icon", "circle").strip()
    priority = data.get("priority", "medium").strip()
    recurrence = data.get("recurrence", "daily").strip()
    recurrence_days = data.get("recurrence_days", "")
    
    if not name:
        return jsonify({"error": "Task name is required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    # Get max order_idx
    cursor.execute("SELECT COALESCE(MAX(order_idx), 0) FROM tasks WHERE user_id = ?;", (user_id,))
    max_order = cursor.fetchone()[0]
    
    try:
        cursor.execute("""
            INSERT INTO tasks (user_id, name, description, category, color, icon, priority, recurrence, recurrence_days, order_idx)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (user_id, name, description, category, color, icon, priority, recurrence, recurrence_days, max_order + 1))
        conn.commit()
        task_id = cursor.lastrowid
        log_event("info", f"Task created: user_id={user_id}, task_id={task_id}, name='{name}'")
        return jsonify({"message": "Task created successfully", "task_id": task_id}), 201
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@tasks_bp.route("/<int:task_id>", methods=["PUT"])
@login_required
def update_task(task_id):
    user_id = request.user["id"]
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    category = data.get("category", "").strip()
    color = data.get("color", "").strip()
    icon = data.get("icon", "").strip()
    priority = data.get("priority", "").strip()
    recurrence = data.get("recurrence", "").strip()
    recurrence_days = data.get("recurrence_days", "")
    is_active = data.get("is_active")
    is_archived = data.get("is_archived")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check ownership
    cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?;", (task_id, user_id))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404
        
    # Build query dynamically
    updates = []
    params = []
    
    if name:
        updates.append("name = ?")
        params.append(name)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if category:
        updates.append("category = ?")
        params.append(category)
    if color:
        updates.append("color = ?")
        params.append(color)
    if icon:
        updates.append("icon = ?")
        params.append(icon)
    if priority:
        updates.append("priority = ?")
        params.append(priority)
    if recurrence:
        updates.append("recurrence = ?")
        params.append(recurrence)
    if recurrence_days is not None:
        updates.append("recurrence_days = ?")
        params.append(recurrence_days)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(int(is_active))
    if is_archived is not None:
        updates.append("is_archived = ?")
        params.append(int(is_archived))
        
    if not updates:
        conn.close()
        return jsonify({"message": "No updates provided"}), 200
        
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?;"
    params.append(task_id)
    
    try:
        cursor.execute(query, params)
        conn.commit()
        log_event("info", f"Task updated: user_id={user_id}, task_id={task_id}")
        return jsonify({"message": "Task updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@tasks_bp.route("/<int:task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    user_id = request.user["id"]
    conn = get_db()
    cursor = conn.cursor()
    
    # Check ownership
    cursor.execute("SELECT name FROM tasks WHERE id = ? AND user_id = ?;", (task_id, user_id))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404
        
    try:
        cursor.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
        conn.commit()
        log_event("info", f"Task deleted: user_id={user_id}, task_id={task_id}, name='{task['name']}'")
        return jsonify({"message": "Task deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@tasks_bp.route("/reorder", methods=["POST"])
@login_required
def reorder_tasks():
    user_id = request.user["id"]
    data = request.get_json() or {}
    ordered_ids = data.get("ordered_ids", [])
    
    if not ordered_ids:
        return jsonify({"error": "ordered_ids is required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Batch update order_idx
        for idx, task_id in enumerate(ordered_ids):
            cursor.execute("UPDATE tasks SET order_idx = ? WHERE id = ? AND user_id = ?;", (idx, task_id, user_id))
        conn.commit()
        return jsonify({"message": "Task order saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@tasks_bp.route("/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    user_id = request.user["id"]
    data = request.get_json() or {}
    date_str = data.get("date") # YYYY-MM-DD
    
    if not date_str:
        return jsonify({"error": "Date is required"}), 400
        
    try:
        datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    # Check ownership
    cursor.execute("SELECT name FROM tasks WHERE id = ? AND user_id = ?;", (task_id, user_id))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404
        
    # Check if already completed
    cursor.execute("SELECT id FROM completions WHERE task_id = ? AND date = ?;", (task_id, date_str))
    completion = cursor.fetchone()
    
    completed_state = 0
    try:
        if completion:
            # Delete completion record (untoggle)
            cursor.execute("DELETE FROM completions WHERE id = ?;", (completion["id"],))
            completed_state = 0
        else:
            # Insert completion record (toggle on)
            cursor.execute("INSERT INTO completions (task_id, date, completed) VALUES (?, ?, 1);", (task_id, date_str))
            completed_state = 1
            
        conn.commit()
        log_event("info", f"Task completion toggled: user_id={user_id}, task_id={task_id}, date={date_str}, completed={completed_state}")
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": f"Database error: {str(e)}"}), 500
        
    conn.close()
    
    # Import streaks calculations dynamically to calculate real-time stats
    from streaks import get_user_stats_summary
    stats = get_user_stats_summary(user_id)
    
    return jsonify({
        "message": "Task toggled successfully",
        "completed": completed_state,
        "stats": stats
    }), 200
