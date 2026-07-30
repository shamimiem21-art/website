import unittest
import os
import json
import sqlite3

# Set custom database path for testing to avoid clobbering development db
os.environ["JWT_SECRET"] = "test-secret-key-12345"
test_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_habitflow.db")

# Override DB_PATH in database module before importing app
import database
database.DB_PATH = test_db_path

from app import app
from database import get_db, init_db

class HabitFlowTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["PROPAGATE_EXCEPTIONS"] = True
        self.client = app.test_client()
        
        # Initialize test database
        init_db()

    def tearDown(self):
        # Remove test database file
        if os.path.exists(test_db_path):
            try:
                os.remove(test_db_path)
            except Exception:
                pass

    def test_database_seeding(self):
        # Check if seed users and categories are loaded
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users;")
        users_count = cursor.fetchone()[0]
        self.assertGreaterEqual(users_count, 2) # Admin and Demo users
        
        cursor.execute("SELECT COUNT(*) FROM categories;")
        cats_count = cursor.fetchone()[0]
        self.assertGreaterEqual(cats_count, 6) # Seed categories
        
        conn.close()

    def test_user_registration_and_verification(self):
        # 1. Register user (auto-verifies and auto-logins)
        reg_payload = {
            "name": "Test User",
            "email": "testuser@domain.com",
            "password": "testpassword"
        }
        res = self.client.post("/api/auth/register", 
                               data=json.dumps(reg_payload), 
                               content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("message", data)
        self.assertEqual(data["user"]["email"], "testuser@domain.com")
        
        # Check that user is in DB and already verified
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT is_verified FROM users WHERE email = 'testuser@domain.com';")
        user = cursor.fetchone()
        self.assertEqual(user["is_verified"], 1)
        conn.close()
        
        # Check that Set-Cookie header contains the token
        cookies = res.headers.getlist("Set-Cookie")
        self.assertTrue(any("habitflow_token" in c for c in cookies))

    def test_user_login_invalid_credentials(self):
        login_payload = {
            "email": "demo@habitflow.com",
            "password": "wrongpassword"
        }
        res = self.client.post("/api/auth/login", 
                               data=json.dumps(login_payload), 
                               content_type="application/json")
        self.assertEqual(res.status_code, 401)

    def test_authenticated_tasks_crud(self):
        # 1. Login as Demo User
        login_payload = {
            "email": "demo@habitflow.com",
            "password": "demopassword"
        }
        login_res = self.client.post("/api/auth/login", 
                                   data=json.dumps(login_payload), 
                                   content_type="application/json")
        self.assertEqual(login_res.status_code, 200)
        
        # Extract cookie
        cookies = login_res.headers.getlist("Set-Cookie")
        token_cookie = [c for c in cookies if "habitflow_token" in c][0]
        
        # Extract JWT value
        jwt_token = token_cookie.split(";")[0].split("=")[1]
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        # 2. Create Task
        task_payload = {
            "name": "Test Habit 1",
            "description": "Verify tasks endpoint working",
            "category": "Fitness",
            "priority": "high",
            "icon": "dumbbell",
            "color": "#4caf50",
            "recurrence": "daily"
        }
        res = self.client.post("/api/tasks", 
                               data=json.dumps(task_payload), 
                               headers=headers,
                               content_type="application/json")
        self.assertEqual(res.status_code, 201)
        task_data = json.loads(res.data)
        task_id = task_data["task_id"]
        
        # 3. Read Tasks
        res = self.client.get("/api/tasks", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertGreaterEqual(len(data["tasks"]), 1)
        
        # 4. Toggle completion
        toggle_payload = {"date": "2026-07-13"}
        res = self.client.post(f"/api/tasks/{task_id}/toggle", 
                               data=json.dumps(toggle_payload),
                               headers=headers,
                               content_type="application/json")
        self.assertEqual(res.status_code, 200)
        toggle_data = json.loads(res.data)
        self.assertEqual(toggle_data["completed"], 1)
        self.assertIn("stats", toggle_data)

        # 5. Delete Task
        res = self.client.delete(f"/api/tasks/{task_id}", headers=headers)
        self.assertEqual(res.status_code, 200)

    def test_admin_authentication_restriction(self):
        # Try to access admin users endpoint as unauthenticated
        res = self.client.get("/api/admin/users")
        self.assertEqual(res.status_code, 401)
        
        # Try to login as regular user and access admin endpoint
        login_payload = {
            "email": "demo@habitflow.com",
            "password": "demopassword"
        }
        login_res = self.client.post("/api/auth/login", 
                                   data=json.dumps(login_payload), 
                                   content_type="application/json")
        cookies = login_res.headers.getlist("Set-Cookie")
        token_cookie = [c for c in cookies if "habitflow_token" in c][0]
        jwt_token = token_cookie.split(";")[0].split("=")[1]
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        res = self.client.get("/api/admin/users", headers=headers)
        self.assertEqual(res.status_code, 403) # Forbidden
        
        # Try to login as Admin and access
        admin_login = {
            "email": "admin@habitflow.com",
            "password": "adminpassword"
        }
        admin_res = self.client.post("/api/auth/admin/login", 
                                    data=json.dumps(admin_login), 
                                    content_type="application/json")
        self.assertEqual(admin_res.status_code, 200)
        
        admin_cookies = admin_res.headers.getlist("Set-Cookie")
        admin_token_cookie = [c for c in admin_cookies if "habitflow_token" in c][0]
        admin_jwt = admin_token_cookie.split(";")[0].split("=")[1]
        admin_headers = {"Authorization": f"Bearer {admin_jwt}"}
        
        res = self.client.get("/api/admin/users", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        users_data = json.loads(res.data)
        self.assertGreaterEqual(len(users_data["users"]), 2)

    def test_analytical_reports(self):
        # 1. Login as Demo User
        login_payload = {
            "email": "demo@habitflow.com",
            "password": "demopassword"
        }
        login_res = self.client.post("/api/auth/login", 
                                   data=json.dumps(login_payload), 
                                   content_type="application/json")
        cookies = login_res.headers.getlist("Set-Cookie")
        token_cookie = [c for c in cookies if "habitflow_token" in c][0]
        jwt_token = token_cookie.split(";")[0].split("=")[1]
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        # 2. Get Weekly Analytical Report
        res = self.client.get("/api/reports/analytical?type=weekly", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("report", data)
        self.assertEqual(data["report"]["report_type"], "weekly")
        self.assertIn("rate_curr", data["report"])
        self.assertIn("breakdown", data["report"])
        self.assertIn("category_analysis", data["report"])
        self.assertIn("habit_analysis", data["report"])
        self.assertIn("suggestions", data["report"])
        
        # 3. Get Monthly Analytical Report
        res = self.client.get("/api/reports/analytical?type=monthly", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["report"]["report_type"], "monthly")
        
        # 4. Try sending report
        send_payload = {"type": "weekly"}
        res = self.client.post("/api/reports/analytical/send", 
                               data=json.dumps(send_payload),
                               headers=headers,
                               content_type="application/json")
        self.assertEqual(res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
