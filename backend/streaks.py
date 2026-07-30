import datetime
from database import get_db

def get_user_stats_summary(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Fetch user tasks
    cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND is_archived = 0;", (user_id,))
    tasks = [dict(t) for t in cursor.fetchall()]
    
    # 2. Fetch all completions for the user
    cursor.execute("""
        SELECT c.date, c.task_id 
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE t.user_id = ?
        ORDER BY c.date DESC
    """, (user_id,))
    completions = [dict(c) for c in cursor.fetchall()]
    conn.close()

    # Organize completions by date
    completions_by_date = {}
    for comp in completions:
        c_date = comp["date"]
        if c_date not in completions_by_date:
            completions_by_date[c_date] = set()
        completions_by_date[c_date].add(comp["task_id"])

    # Helper: Check if task was scheduled on a given date
    def is_scheduled(task, check_date):
        created_at = task["created_at"]
        try:
            # Parse created date
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
        elif recurrence == "weekly":
            days = task["recurrence_days"]
            if not days:
                return True
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            check_day_name = day_names[check_date.weekday()]
            active_days = [d.strip() for d in days.split(",")]
            return check_day_name in active_days
        return True

    # Calculate streaks (overall)
    # Consecutive days with at least one task completed
    today = datetime.date.today()
    current_streak = 0
    longest_streak = 0
    
    # Sort all completion dates
    sorted_comp_dates = sorted(list(completions_by_date.keys()), reverse=True)
    comp_dates_set = set()
    for d_str in completions_by_date.keys():
        try:
            comp_dates_set.add(datetime.date.fromisoformat(d_str))
        except ValueError:
            pass

    # Check current streak
    check_day = today
    if check_day not in comp_dates_set:
        check_day = today - datetime.timedelta(days=1) # if not today, check yesterday
        
    while check_day in comp_dates_set:
        current_streak += 1
        check_day -= datetime.timedelta(days=1)

    # Check longest streak
    temp_streak = 0
    sorted_unique_dates = sorted(list(comp_dates_set))
    if sorted_unique_dates:
        prev_date = None
        for d in sorted_unique_dates:
            if prev_date is None:
                temp_streak = 1
            elif (d - prev_date).days == 1:
                temp_streak += 1
            elif (d - prev_date).days > 1:
                if temp_streak > longest_streak:
                    longest_streak = temp_streak
                temp_streak = 1
            prev_date = d
        if temp_streak > longest_streak:
            longest_streak = temp_streak
    else:
        longest_streak = 0

    # Calculate Weekly and Monthly statistics (last 7 days and last 30 days)
    last_7_days = [today - datetime.timedelta(days=i) for i in range(7)]
    last_30_days = [today - datetime.timedelta(days=i) for i in range(30)]
    
    scheduled_7_count = 0
    completed_7_count = 0
    scheduled_30_count = 0
    completed_30_count = 0
    
    for d in last_7_days:
        d_str = d.isoformat()
        day_completions = completions_by_date.get(d_str, set())
        for task in tasks:
            if is_scheduled(task, d):
                scheduled_7_count += 1
                if task["id"] in day_completions:
                    completed_7_count += 1

    for d in last_30_days:
        d_str = d.isoformat()
        day_completions = completions_by_date.get(d_str, set())
        for task in tasks:
            if is_scheduled(task, d):
                scheduled_30_count += 1
                if task["id"] in day_completions:
                    completed_30_count += 1

    weekly_pct = round((completed_7_count / scheduled_7_count * 100), 1) if scheduled_7_count > 0 else 0.0
    monthly_pct = round((completed_30_count / scheduled_30_count * 100), 1) if scheduled_30_count > 0 else 0.0
    
    total_completed = len(completions)
    
    # Estimate total missed tasks in the last 30 days
    total_missed_30 = scheduled_30_count - completed_30_count

    # Calculate consistency score
    # Formula: 70% weekly completion + 30% streak bonus (capped at 30 days)
    streak_bonus = min(current_streak, 30) / 30.0 * 30.0
    consistency_score = round((weekly_pct * 0.7) + streak_bonus, 1)

    # Perfect weeks and perfect months
    # A perfect week: rolling last 7 days where weekly completion is 100% (or calendar weeks)
    # Let's count calendar weeks (Mon-Sun) in the database with 100% completion
    # We can approximate perfect weeks and months by checking last 4 calendar weeks
    perfect_weeks = 0
    for w in range(4):
        w_start = today - datetime.timedelta(days=today.weekday() + 7*w) # Monday of week w
        w_days = [w_start + datetime.timedelta(days=i) for i in range(7)]
        w_sched = 0
        w_comp = 0
        for wd in w_days:
            wd_str = wd.isoformat()
            wd_completions = completions_by_date.get(wd_str, set())
            for task in tasks:
                if is_scheduled(task, wd):
                    w_sched += 1
                    if task["id"] in wd_completions:
                        w_comp += 1
        if w_sched > 0 and w_comp == w_sched:
            perfect_weeks += 1

    # Perfect months (current calendar month and previous calendar month)
    perfect_months = 0
    current_month = today.month
    current_year = today.year
    # Let's check current month completions so far
    m_sched = 0
    m_comp = 0
    for day_offset in range((today - today.replace(day=1)).days + 1):
        md = today.replace(day=1) + datetime.timedelta(days=day_offset)
        md_str = md.isoformat()
        md_completions = completions_by_date.get(md_str, set())
        for task in tasks:
            if is_scheduled(task, md):
                m_sched += 1
                if task["id"] in md_completions:
                    m_comp += 1
    if m_sched > 0 and m_comp == m_sched:
        perfect_months += 1

    # Badges earned
    badges = []
    if total_completed >= 1:
        badges.append({"id": "seedling", "name": "Seedling", "desc": "First habit completed! 🌱", "icon": "seedling"})
    if current_streak >= 3:
        badges.append({"id": "sprout", "name": "Sprout", "desc": "3-day streak active!", "icon": "spa"})
    if current_streak >= 7:
        badges.append({"id": "sapling", "name": "Sapling", "desc": "7-day streak active! 🌿", "icon": "tree"})
    if current_streak >= 30:
        badges.append({"id": "oak", "name": "Ancient Oak", "desc": "30-day streak achieved! 🌳", "icon": "forest"})
    if perfect_weeks >= 1:
        badges.append({"id": "perfect_week", "name": "Perfect Week", "desc": "100% week completed! 🏆", "icon": "award"})
    if consistency_score >= 90:
        badges.append({"id": "habit_master", "name": "Habit Master", "desc": "Consistency score over 90!", "icon": "crown"})

    # Calendar Heatmap (Last 365 Days)
    heatmap = {}
    for i in range(365):
        d = today - datetime.timedelta(days=i)
        d_str = d.isoformat()
        completed_count = len(completions_by_date.get(d_str, []))
        if completed_count > 0:
            heatmap[d_str] = completed_count

    return {
        "current_date": today.strftime("%A, %B %d, %Y"),
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "weekly_pct": weekly_pct,
        "monthly_pct": monthly_pct,
        "total_completed": total_completed,
        "total_missed_30": total_missed_30,
        "productivity_score": consistency_score, # Alias
        "consistency_score": consistency_score,
        "perfect_weeks": perfect_weeks,
        "perfect_months": perfect_months,
        "badges": badges,
        "heatmap": heatmap
    }

def get_detailed_analytics(user_id):
    summary = get_user_stats_summary(user_id)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Fetch user tasks
    cursor.execute("SELECT id, name, category, created_at, is_active FROM tasks WHERE user_id = ? AND is_archived = 0;", (user_id,))
    tasks = [dict(t) for t in cursor.fetchall()]
    
    # 2. Completion rates per task
    task_stats = []
    best_habit = None
    worst_habit = None
    most_skipped = None
    most_consistent = None
    
    highest_rate = -1
    lowest_rate = 101
    max_completions = -1
    max_misses = -1
    
    for t in tasks:
        t_id = t["id"]
        # Total completions
        cursor.execute("SELECT COUNT(*) FROM completions WHERE task_id = ?;", (t_id,))
        completions_count = cursor.fetchone()[0]
        
        # Calculate scheduled days since creation (up to last 30 days)
        # Let's count how many days it was scheduled
        created_at = t["created_at"]
        try:
            created_date = datetime.datetime.strptime(created_at.split(" ")[0], "%Y-%m-%d").date()
        except Exception:
            created_date = datetime.date.today() - datetime.timedelta(days=30)
            
        today = datetime.date.today()
        start_date = max(created_date, today - datetime.timedelta(days=30))
        
        scheduled_days = 0
        actual_completed = 0
        
        # Query if completed for each date
        cursor.execute("SELECT date FROM completions WHERE task_id = ?;", (t_id,))
        completion_dates = {row["date"] for row in cursor.fetchall()}
        
        # Helper recurrence check
        def is_scheduled_recurrence(task, check_date):
            # Same logic
            cursor.execute("SELECT recurrence, recurrence_days, is_active FROM tasks WHERE id = ?;", (task["id"],))
            task_data = cursor.fetchone()
            if not task_data or task_data["is_active"] == 0:
                return False
            rec = task_data["recurrence"]
            if rec == "daily":
                return True
            elif rec == "weekly":
                days = task_data["recurrence_days"]
                if not days:
                    return True
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                active_days = [d.strip() for d in days.split(",")]
                return day_names[check_date.weekday()] in active_days
            return True

        curr_d = start_date
        while curr_d <= today:
            if is_scheduled_recurrence(t, curr_d):
                scheduled_days += 1
                if curr_d.isoformat() in completion_dates:
                    actual_completed += 1
            curr_d += datetime.timedelta(days=1)
            
        rate = round((actual_completed / scheduled_days * 100), 1) if scheduled_days > 0 else 0.0
        missed = max(0, scheduled_days - actual_completed)
        
        stat = {
            "id": t_id,
            "name": t["name"],
            "category": t["category"],
            "completion_rate": rate,
            "completions": completions_count,
            "misses": missed
        }
        task_stats.append(stat)
        
        if scheduled_days > 0:
            if rate > highest_rate:
                highest_rate = rate
                best_habit = t["name"]
            if rate < lowest_rate:
                lowest_rate = rate
                worst_habit = t["name"]
            if completions_count > max_completions:
                max_completions = completions_count
                most_consistent = t["name"]
            if missed > max_misses:
                max_misses = missed
                most_skipped = t["name"]

    # 3. Category completions
    cursor.execute("""
        SELECT t.category, COUNT(c.id) as count
        FROM completions c
        JOIN tasks t ON c.task_id = t.id
        WHERE t.user_id = ?
        GROUP BY t.category
    """, (user_id,))
    category_counts = {row["category"]: row["count"] for row in cursor.fetchall()}
    
    # 4. Daily completion chart data for the last 7 days
    daily_labels = []
    daily_values = []
    today = datetime.date.today()
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        d_str = d.isoformat()
        
        # Scheduled count
        sched_count = 0
        comp_count = 0
        
        cursor.execute("SELECT id FROM completions WHERE date = ? AND task_id IN (SELECT id FROM tasks WHERE user_id = ?);", (d_str, user_id))
        completed_ids = {row[0] for row in cursor.fetchall()}
        
        for t in tasks:
            # Fetch recurrence info to check if scheduled
            cursor.execute("SELECT recurrence, recurrence_days, is_active, created_at FROM tasks WHERE id = ?;", (t["id"],))
            t_info = cursor.fetchone()
            if not t_info:
                continue
            
            created_date = datetime.datetime.strptime(t_info["created_at"].split(" ")[0], "%Y-%m-%d").date()
            if created_date > d:
                continue
                
            if t_info["is_active"] == 0:
                continue
                
            is_sched = True
            rec = t_info["recurrence"]
            if rec == "weekly":
                days = t_info["recurrence_days"]
                if days:
                    active_days = [day.strip() for day in days.split(",")]
                    is_sched = day_names[d.weekday()] in active_days
                    
            if is_sched:
                sched_count += 1
                if t["id"] in completed_ids:
                    comp_count += 1
                    
        rate = round((comp_count / sched_count * 100), 1) if sched_count > 0 else 0.0
        daily_labels.append(d.strftime("%a (%m/%d)"))
        daily_values.append(rate)

    conn.close()
    
    return {
        "summary": summary,
        "task_stats": task_stats,
        "best_habit": best_habit or "None yet",
        "worst_habit": worst_habit or "None yet",
        "most_skipped_habit": most_skipped or "None yet",
        "most_consistent_habit": most_consistent or "None yet",
        "category_completion": category_counts,
        "chart_daily": {
            "labels": daily_labels,
            "data": daily_values
        }
    }
