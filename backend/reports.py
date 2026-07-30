import datetime
from flask import Blueprint, jsonify, request
from auth import login_required
from database import get_db, log_event
from streaks import get_detailed_analytics
from email_service import send_email

reports_bp = Blueprint("reports", __name__)

def generate_weekly_report_data(user_id):
    analytics = get_detailed_analytics(user_id)
    summary = analytics["summary"]
    
    # Category list formatting
    categories_formatted = []
    for cat, count in analytics["category_completion"].items():
        categories_formatted.append(f"{cat}: {count} completions")
    category_summary = ", ".join(categories_formatted) if categories_formatted else "No categories logged yet."

    # Dynamic suggestions based on scores
    suggestions = []
    weekly_pct = summary["weekly_pct"]
    
    if weekly_pct >= 90:
        suggestions.append("Outstanding work! You've achieved elite consistency this week. Keep running with this momentum!")
        suggestions.append("Consider raising the bar: add 10 more minutes to your study or exercise habits.")
    elif weekly_pct >= 70:
        suggestions.append("Solid performance! You are establishing a strong routine. Keep focused on your highest priority habits.")
        suggestions.append("Try setting a specific reminder time for your most skipped habit to lock it in.")
    elif weekly_pct >= 45:
        suggestions.append("You are in the building phase. It is normal to hit bumps in the road. Focus on consistency over perfection.")
        suggestions.append("Tip: Focus on completing just your top 2 priority tasks every single day this week.")
    else:
        suggestions.append("A fresh week is a fresh start! Don't be discouraged by a low score.")
        suggestions.append("Action item: Temporarily set some tasks to 'inactive' so you can focus 100% on just one core habit.")
        
    # Analyze best and worst habits
    if analytics["best_habit"] != "None yet" and weekly_pct > 0:
        suggestions.append(f"Your best habit was '{analytics['best_habit']}'. Reflect on why this was successful and apply that environment to other tasks.")
    if analytics["worst_habit"] != "None yet" and weekly_pct < 100:
        suggestions.append(f"Your most skipped habit was '{analytics['worst_habit']}'. Consider breaking it into a smaller, 5-minute chunk (e.g. 'Study 5 mins' instead of 'Study 30 mins').")

    report_data = {
        "weekly_pct": weekly_pct,
        "completed_count": summary["total_completed"],
        "missed_count_30": summary["total_missed_30"],
        "current_streak": summary["current_streak"],
        "longest_streak": summary["longest_streak"],
        "best_habit": analytics["best_habit"],
        "worst_habit": analytics["worst_habit"],
        "category_summary": category_summary,
        "suggestions": suggestions,
        "heatmap": summary["heatmap"],
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return report_data

def generate_analytical_report_data(user_id, report_type, offset=0):
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Fetch user tasks
    cursor.execute("SELECT * FROM tasks WHERE user_id = ?;", (user_id,))
    tasks = [dict(t) for t in cursor.fetchall()]
    
    # Helper to check if task was scheduled on a given date
    def is_scheduled(task, check_date):
        created_at = task["created_at"]
        try:
            created_date = datetime.datetime.strptime(created_at.split(" ")[0], "%Y-%m-%d").date()
            if created_date > check_date:
                return False
        except Exception:
            pass

        if task["is_active"] == 0 and not task["is_archived"]:
            return False
            
        recurrence = task["recurrence"]
        if recurrence == "daily":
            return True
        elif recurrence == "weekly":
            days = task["recurrence_days"]
            if not days:
                return True
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            check_day_name = day_names[check_date.weekday()]
            active_days = [d.strip() for d in days.split(",")]
            return check_day_name in active_days
        return True

    today = datetime.date.today()
    
    if report_type == "weekly":
        days_count = 7
        current_end = today - datetime.timedelta(weeks=offset)
        current_start = current_end - datetime.timedelta(days=6)
        prev_end = current_start - datetime.timedelta(days=1)
        prev_start = prev_end - datetime.timedelta(days=6)
    else: # monthly
        days_count = 30
        current_end = today - datetime.timedelta(days=30*offset)
        current_start = current_end - datetime.timedelta(days=29)
        prev_end = current_start - datetime.timedelta(days=1)
        prev_start = prev_end - datetime.timedelta(days=29)
        
    # Fetch completions in both ranges
    cursor.execute("""
        SELECT c.date, c.task_id 
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE t.user_id = ? AND c.date BETWEEN ? AND ?
    """, (user_id, prev_start.isoformat(), current_end.isoformat()))
    completions = [dict(c) for c in cursor.fetchall()]
    conn.close()
    
    # Organize completions
    completions_current = {}
    completions_prev = {}
    
    for c in completions:
        try:
            c_date = datetime.date.fromisoformat(c["date"])
            t_id = c["task_id"]
            if current_start <= c_date <= current_end:
                if c["date"] not in completions_current:
                    completions_current[c["date"]] = set()
                completions_current[c["date"]].add(t_id)
            elif prev_start <= c_date <= prev_end:
                if c["date"] not in completions_prev:
                    completions_prev[c["date"]] = set()
                completions_prev[c["date"]].add(t_id)
        except ValueError:
            pass

    # Current Period Totals
    scheduled_curr = 0
    completed_curr = 0
    
    # Track metrics per task for current period
    task_metrics = {}
    for t in tasks:
        task_metrics[t["id"]] = {
            "name": t["name"], 
            "category": t["category"], 
            "scheduled": 0, 
            "completed": 0, 
            "color": t["color"], 
            "icon": t["icon"]
        }

    # Day-of-week analysis
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_stats = {name: {"scheduled": 0, "completed": 0} for name in day_names}
    
    # Loop current period days
    curr_d = current_start
    while curr_d <= current_end:
        d_str = curr_d.isoformat()
        d_name = day_names[curr_d.weekday()]
        day_completions = completions_current.get(d_str, set())
        
        for t in tasks:
            if is_scheduled(t, curr_d):
                scheduled_curr += 1
                day_stats[d_name]["scheduled"] += 1
                task_metrics[t["id"]]["scheduled"] += 1
                
                if t["id"] in day_completions:
                    completed_curr += 1
                    day_stats[d_name]["completed"] += 1
                    task_metrics[t["id"]]["completed"] += 1
                    
        curr_d += datetime.timedelta(days=1)

    # Previous Period Totals
    scheduled_prev = 0
    completed_prev = 0
    
    # Loop previous period days
    prev_d = prev_start
    while prev_d <= prev_end:
        d_str = prev_d.isoformat()
        day_completions = completions_prev.get(d_str, set())
        
        for t in tasks:
            if is_scheduled(t, prev_d):
                scheduled_prev += 1
                if t["id"] in day_completions:
                    completed_prev += 1
        prev_d += datetime.timedelta(days=1)

    # Completion rates
    rate_curr = round((completed_curr / scheduled_curr * 100), 1) if scheduled_curr > 0 else 0.0
    rate_prev = round((completed_prev / scheduled_prev * 100), 1) if scheduled_prev > 0 else 0.0
    trend = round(rate_curr - rate_prev, 1)

    # Category analysis
    category_stats = {}
    for t_id, m in task_metrics.items():
        cat = m["category"]
        if cat not in category_stats:
            category_stats[cat] = {"scheduled": 0, "completed": 0}
        category_stats[cat]["scheduled"] += m["scheduled"]
        category_stats[cat]["completed"] += m["completed"]
        
    category_analysis = []
    for cat, stats in category_stats.items():
        rate = round((stats["completed"] / stats["scheduled"] * 100), 1) if stats["scheduled"] > 0 else 0.0
        category_analysis.append({
            "category": cat,
            "scheduled": stats["scheduled"],
            "completed": stats["completed"],
            "completion_rate": rate
        })
        
    # Habit list analysis
    habit_analysis = []
    best_habit = None
    worst_habit = None
    best_rate = -1
    worst_rate = 101
    
    for t_id, m in task_metrics.items():
        if m["scheduled"] > 0:
            rate = round((m["completed"] / m["scheduled"] * 100), 1)
            habit_analysis.append({
                "id": t_id,
                "name": m["name"],
                "category": m["category"],
                "color": m["color"],
                "icon": m["icon"],
                "scheduled": m["scheduled"],
                "completed": m["completed"],
                "rate": rate
            })
            if rate > best_rate:
                best_rate = rate
                best_habit = {"name": m["name"], "rate": rate}
            if rate < worst_rate:
                worst_rate = rate
                worst_habit = {"name": m["name"], "rate": rate}
                
    # Day-of-week list
    day_analysis = []
    best_day_name = None
    worst_day_name = None
    best_day_rate = -1
    worst_day_rate = 101
    
    for d_name in day_names:
        stats = day_stats[d_name]
        rate = round((stats["completed"] / stats["scheduled"] * 100), 1) if stats["scheduled"] > 0 else 0.0
        day_analysis.append({
            "day": d_name,
            "scheduled": stats["scheduled"],
            "completed": stats["completed"],
            "rate": rate
        })
        if stats["scheduled"] > 0:
            if rate > best_day_rate:
                best_day_rate = rate
                best_day_name = d_name
            if rate < worst_day_rate:
                worst_day_rate = rate
                worst_day_name = d_name

    # Weekly breakdowns or daily breakdowns
    breakdown_data = []
    if report_type == "weekly":
        # 7 individual days
        curr_d = current_start
        while curr_d <= current_end:
            d_str = curr_d.isoformat()
            d_name = day_names[curr_d.weekday()][:3]
            day_completions = completions_current.get(d_str, set())
            
            d_sched = 0
            d_comp = 0
            for t in tasks:
                if is_scheduled(t, curr_d):
                    d_sched += 1
                    if t["id"] in day_completions:
                        d_comp += 1
            rate = round((d_comp / d_sched * 100), 1) if d_sched > 0 else 0.0
            breakdown_data.append({
                "label": f"{d_name} ({curr_d.month}/{curr_d.day})",
                "completed": d_comp,
                "scheduled": d_sched,
                "rate": rate
            })
            curr_d += datetime.timedelta(days=1)
    else:
        # 4 weeks of the month
        for w in range(4):
            w_start = today - datetime.timedelta(days=7*w + 6 if w < 3 else 29)
            w_end = today - datetime.timedelta(days=7*w)
            
            w_sched = 0
            w_comp = 0
            
            curr_d = w_start
            while curr_d <= w_end:
                d_str = curr_d.isoformat()
                day_completions = completions_current.get(d_str, set())
                if not day_completions:
                    day_completions = completions_prev.get(d_str, set())
                    
                for t in tasks:
                    if is_scheduled(t, curr_d):
                        w_sched += 1
                        if t["id"] in day_completions:
                            w_comp += 1
                curr_d += datetime.timedelta(days=1)
                
            rate = round((w_comp / w_sched * 100), 1) if w_sched > 0 else 0.0
            breakdown_data.insert(0, {
                "label": f"Week {4-w} ({w_start.month}/{w_start.day}-{w_end.month}/{w_end.day})",
                "completed": w_comp,
                "scheduled": w_sched,
                "rate": rate
            })
    # Calculate streaks within the range [current_start, current_end]
    range_completed_dates = set()
    for d_str, task_ids in completions_current.items():
        if len(task_ids) > 0:
            try:
                range_completed_dates.add(datetime.date.fromisoformat(d_str))
            except ValueError:
                pass
                
    # Longest and current streak in this range
    longest_streak_in_range = 0
    current_streak_in_range = 0
    
    # Sort completed dates
    sorted_range_dates = sorted(list(range_completed_dates))
    if sorted_range_dates:
        temp_streak = 0
        prev_date = None
        for d in sorted_range_dates:
            if prev_date is None:
                temp_streak = 1
            elif (d - prev_date).days == 1:
                temp_streak += 1
            else:
                if temp_streak > longest_streak_in_range:
                    longest_streak_in_range = temp_streak
                temp_streak = 1
            prev_date = d
        if temp_streak > longest_streak_in_range:
            longest_streak_in_range = temp_streak
            
        # Current streak at the end of range (counting backwards from current_end)
        check_d = current_end
        if check_d not in range_completed_dates and (current_end == today or current_end == today - datetime.timedelta(days=1)):
            if (current_end - datetime.timedelta(days=1)) in range_completed_dates:
                check_d = current_end - datetime.timedelta(days=1)
        
        while check_d in range_completed_dates and check_d >= current_start:
            current_streak_in_range += 1
            check_d -= datetime.timedelta(days=1)
            
    # Track missed counts per task to find the most skipped task
    most_skipped_name = "N/A"
    most_skipped_count = -1
    for t_id, m in task_metrics.items():
        missed = m["scheduled"] - m["completed"]
        if missed > most_skipped_count and m["scheduled"] > 0:
            most_skipped_count = missed
            most_skipped_name = m["name"]
            
    # Generate daily completions map for monthly heatmap/detailed trend
    daily_completions_map = {}
    curr_d = current_start
    while curr_d <= current_end:
        d_str = curr_d.isoformat()
        day_completions = completions_current.get(d_str, set())
        
        d_sched = 0
        d_comp = 0
        for t in tasks:
            if is_scheduled(t, curr_d):
                d_sched += 1
                if t["id"] in day_completions:
                    d_comp += 1
        daily_completions_map[d_str] = {
            "completed": d_comp,
            "scheduled": d_sched,
            "rate": round((d_comp / d_sched * 100), 1) if d_sched > 0 else 0.0
        }
        curr_d += datetime.timedelta(days=1)

    # Suggestions
    suggestions = []
    if rate_curr >= 85:
        suggestions.append("Exceptional consistency! You have established automatic, high-performing neural routines. Consider scaling up your target durations (e.g., exercise 45 minutes instead of 30) or adding a high-priority challenge.")
    elif rate_curr >= 65:
        suggestions.append("Strong habits are forming! Your foundation is stable. To take it to the next level, focus on eliminating friction from your lowest-performing categories.")
    else:
        suggestions.append("You are in the building phase. To build consistency, reduce your daily schedule to just 1 or 2 high-priority habits. Remember, doing 2 minutes of a habit is better than skipping it entirely.")
        
    if best_day_name:
        suggestions.append(f"Your analytical peak occurs on **{best_day_name}** ({best_day_rate}%). Observe what goes right on this day—environment, sleep, routine—and try to duplicate it elsewhere.")
    if worst_day_name and worst_day_rate < 50:
        suggestions.append(f"Your consistency dips to {worst_day_rate}% on **{worst_day_name}**. Plan ahead for this day by reducing task friction or moving heavy habits to earlier in the week.")
    if worst_habit and worst_habit["rate"] < 50:
        suggestions.append(f"The habit **'{worst_habit['name']}'** has a completion rate of only {worst_habit['rate']}%. Consider breaking it down into a tiny task (e.g., 'read 1 page' instead of 'study 30 minutes').")

    return {
        "report_type": report_type,
        "days_count": days_count,
        "current_start": current_start.isoformat(),
        "current_end": current_end.isoformat(),
        "scheduled_curr": scheduled_curr,
        "completed_curr": completed_curr,
        "missed_curr": scheduled_curr - completed_curr,
        "current_streak": current_streak_in_range,
        "longest_streak": longest_streak_in_range,
        "most_skipped_habit": most_skipped_name,
        "productivity_score": round((rate_curr * 0.7) + (min(current_streak_in_range, 30) / 30.0 * 30.0), 1),
        "consistency_score": round((rate_curr * 0.7) + (min(current_streak_in_range, 30) / 30.0 * 30.0), 1),
        "daily_completions": daily_completions_map,
        "offset": offset,
        "rate_curr": rate_curr,
        "rate_prev": rate_prev,
        "trend": trend,
        "best_day": best_day_name or "N/A",
        "best_day_rate": best_day_rate,
        "worst_day": worst_day_name or "N/A",
        "worst_day_rate": worst_day_rate,
        "best_habit": best_habit["name"] if best_habit else "N/A",
        "best_habit_rate": best_habit["rate"] if best_habit else 0.0,
        "worst_habit": worst_habit["name"] if worst_habit else "N/A",
        "worst_habit_rate": worst_habit["rate"] if worst_habit else 0.0,
        "category_analysis": category_analysis,
        "habit_analysis": habit_analysis,
        "day_analysis": day_analysis,
        "breakdown": breakdown_data,
        "suggestions": suggestions,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def compile_analytical_report_html(report_data, name):
    suggestions_html = "".join([f"<li style='margin-bottom: 8px; color: #333;'>{s}</li>" for s in report_data["suggestions"]])
    breakdown_rows = ""
    for b in report_data["breakdown"]:
        breakdown_rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{b["label"]}</td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{b["completed"]}/{b["scheduled"]}</td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right; font-weight: bold; color: #2d5a27;">{b["rate"]}%</td>
        </tr>
        """
        
    trend_color = "#2e7d32" if report_data["trend"] >= 0 else "#c62828"
    trend_arrow = "↑" if report_data["trend"] >= 0 else "↓"
    trend_text = f"{trend_arrow} {abs(report_data['trend'])}% vs previous period"
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e8e0; border-radius: 8px; background-color: #fcfdfc;">
        <div style="text-align: center; border-bottom: 2px solid #2d5a27; padding-bottom: 15px; margin-bottom: 20px;">
            <span style="font-size: 40px;">📊</span>
            <h2 style="color: #2d5a27; margin: 5px 0;">Analytical {report_data["report_type"].capitalize()} Report</h2>
            <p style="color: #666; margin: 0;">HabitFlow Progress Analytics for {name}</p>
        </div>
        
        <div style="background-color: #f4f8f4; border: 1px solid #d8ebd4; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
            <span style="font-size: 14px; color: #666; display: block; text-transform: uppercase;">Completion Rate</span>
            <span style="font-size: 36px; font-weight: bold; color: #2d5a27; display: block; margin: 5px 0;">{report_data["rate_curr"]}%</span>
            <span style="font-size: 13px; color: {trend_color}; font-weight: bold;">{trend_text}</span>
        </div>
        
        <h3 style="color: #2d5a27; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Key Metrics</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
                <td style="padding: 8px 0; color: #555;">Completed Tasks:</td>
                <td style="padding: 8px 0; font-weight: bold; text-align: right;">{report_data["completed_curr"]}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #555;">Scheduled Tasks:</td>
                <td style="padding: 8px 0; font-weight: bold; text-align: right;">{report_data["scheduled_curr"]}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #555;">Best Performing Habit:</td>
                <td style="padding: 8px 0; font-weight: bold; text-align: right; color: #2d5a27;">{report_data["best_habit"]} ({report_data["best_habit_rate"]}%)</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #555;">Most Missed Habit:</td>
                <td style="padding: 8px 0; font-weight: bold; text-align: right; color: #d32f2f;">{report_data["worst_habit"]} ({report_data["worst_habit_rate"]}%)</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #555;">Peak Weekday:</td>
                <td style="padding: 8px 0; font-weight: bold; text-align: right;">{report_data["best_day"]} ({report_data["best_day_rate"]}%)</td>
            </tr>
        </table>
        
        <h3 style="color: #2d5a27; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Period Breakdown</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <thead>
                <tr style="background-color: #eee;">
                    <th style="padding: 8px; text-align: left;">Period</th>
                    <th style="padding: 8px; text-align: right;">Completions</th>
                    <th style="padding: 8px; text-align: right;">Rate</th>
                </tr>
            </thead>
            <tbody>
                {breakdown_rows}
            </tbody>
        </table>
        
        <h3 style="color: #2d5a27; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Personalized Behavioral Insights</h3>
        <ul style="padding-left: 20px; line-height: 1.5; margin: 0 0 20px;">
            {suggestions_html}
        </ul>
        
        <div style="text-align: center; border-top: 1px solid #eee; padding-top: 15px; font-size: 11px; color: #888;">
            Generated by HabitFlow 🌿 at {report_data["generated_at"]}
        </div>
    </div>
    """
    return html

# BACKWARD COMPATIBLE WEEKLY REPORT
@reports_bp.route("/weekly", methods=["GET"])
@login_required
def get_weekly_report():
    user_id = request.user["id"]
    try:
        report_data = generate_weekly_report_data(user_id)
        return jsonify({"report": report_data})
    except Exception as e:
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500

@reports_bp.route("/weekly/send", methods=["POST"])
@login_required
def send_weekly_report():
    user_id = request.user["id"]
    email = request.user["email"]
    name = request.user["name"]
    
    try:
        report_data = generate_weekly_report_data(user_id)
        # compile old format HTML (kept for compatibility)
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
            log_event("info", f"Weekly report email sent to: {email}")
            return jsonify({"message": "Weekly email report sent successfully!"})
        else:
            return jsonify({"error": "Failed to send email"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# NEW ANALYTICAL ENDPOINTS
@reports_bp.route("/analytical", methods=["GET"])
@login_required
def get_analytical_report():
    user_id = request.user["id"]
    report_type = request.args.get("type", "weekly")
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        offset = 0
        
    if report_type not in ["weekly", "monthly"]:
        return jsonify({"error": "Invalid report type. Must be 'weekly' or 'monthly'"}), 400
        
    try:
        data = generate_analytical_report_data(user_id, report_type, offset)
        return jsonify({"report": data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate analytical report: {str(e)}"}), 500

@reports_bp.route("/analytical/send", methods=["POST"])
@login_required
def send_analytical_report():
    user_id = request.user["id"]
    email = request.user["email"]
    name = request.user["name"]
    
    data = request.get_json() or {}
    report_type = data.get("type", "weekly")
    try:
        offset = int(data.get("offset", 0))
    except ValueError:
        offset = 0
        
    if report_type not in ["weekly", "monthly"]:
        return jsonify({"error": "Invalid report type"}), 400
        
    try:
        report_data = generate_analytical_report_data(user_id, report_type, offset)
        report_html = compile_analytical_report_html(report_data, name)
        
        subject = f"Your HabitFlow Analytical {report_type.capitalize()} Report 📊"
        success = send_email(email, subject, report_html, f"analytical_{report_type}")
        
        if success:
            log_event("info", f"Analytical {report_type} email report sent to: {email}")
            return jsonify({"message": f"Analytical {report_type} report email sent successfully!"})
        else:
            return jsonify({"error": "Failed to send email"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
