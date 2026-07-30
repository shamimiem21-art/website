import sqlite3
import datetime
import random
import os

DB_PATH = r"C:\Users\Acer\.gemini\antigravity\scratch\habitflow\backend\habitflow.db"

def populate():
    print("Populating database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute("SELECT id, email FROM users")
    users = cursor.fetchall()
    
    for user_id, email in users:
        print(f"Populating data for user {email} (ID: {user_id})...")
        
        # Check if tasks already exist to avoid duplication
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] > 0:
            print(f"Tasks already exist for {email}. Clearing old data for a fresh showcase...")
            cursor.execute("DELETE FROM completions WHERE task_id IN (SELECT id FROM tasks WHERE user_id = ?)", (user_id,))
            cursor.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
            
        tasks = [
            ("Drink Water", "Drink 2 liters of water daily", "Health", "#3498db", "tint", "high", "daily", ""),
            ("Read 20 Pages", "Read a non-fiction book", "Learning", "#9b59b6", "book", "medium", "daily", ""),
            ("Morning Run", "Run 3km in the morning", "Fitness", "#e74c3c", "running", "high", "weekly", "Mon,Wed,Fri"),
            ("Meditate", "10 minutes of mindfulness", "Wellness", "#2ecc71", "spa", "medium", "daily", ""),
            ("Write Code", "Work on personal project", "Career", "#f1c40f", "code", "high", "daily", ""),
            ("Stretch", "15 mins full body stretch", "Fitness", "#e67e22", "child", "low", "weekly", "Tue,Thu,Sat,Sun")
        ]
        
        task_ids = []
        order = 0
        for t in tasks:
            cursor.execute("""
                INSERT INTO tasks (user_id, name, description, category, color, icon, priority, recurrence, recurrence_days, order_idx)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], order))
            task_ids.append((cursor.lastrowid, t))
            order += 1
            
        print(f"Created {len(task_ids)} tasks for {email}.")
        
        # Generate completions for the last 60 days
        today = datetime.date.today()
        completions = 0
        for i in range(60):
            current_date = today - datetime.timedelta(days=i)
            date_str = current_date.isoformat()
            
            # Weekday: 0=Mon, 6=Sun
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            day_name = day_names[current_date.weekday()]
            
            for t_id, t_info in task_ids:
                recurrence = t_info[6]
                days = t_info[7]
                
                # Check if scheduled for this day
                scheduled = False
                if recurrence == "daily":
                    scheduled = True
                elif recurrence == "weekly" and day_name in days:
                    scheduled = True
                    
                if scheduled:
                    # Randomly complete based on some probabilities to make charts look real
                    prob = 0.75
                    if t_info[0] == "Drink Water": prob = 0.95
                    elif t_info[0] == "Morning Run": prob = 0.50
                    elif t_info[0] == "Meditate": prob = 0.65
                    
                    if i < 14: prob += 0.1
                    
                    if random.random() < prob:
                        cursor.execute("INSERT INTO completions (task_id, date) VALUES (?, ?)", (t_id, date_str))
                        completions += 1
                        
        print(f"Generated {completions} completions for {email}.")
                    
    conn.commit()
    conn.close()
    print("Database populated successfully for all users!")

if __name__ == "__main__":
    populate()
