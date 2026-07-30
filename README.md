# HabitFlow 🌿

> **HabitFlow** is a modern, nature-inspired, production-ready habit and daily task tracking web application. Built with modern UI aesthetics, dynamic single-page routing, rich analytical reports, automatic streak calculation, and an elevated Admin Management Terminal.

---

## 🌟 Key Features

### 🌿 User Experience & Design
- **Nature-Inspired Interface**: Modern glassmorphism layout, soothing color palette, soft cards, smooth transitions, and responsive mobile-first UI.
- **Dark Mode / Light Mode**: Toggle themes seamlessly with automatic theme persistence across devices.
- **Embedded Today's Habits Checklist**: View and complete your daily habits directly from the Dashboard without navigating away.

### 📋 Daily Task Tracker & Customization
- **Weekly Progress Grid**: 7-day completion matrix for every habit (Sunday through Saturday).
- **Drag-and-Drop Reordering**: Drag tasks to reorder them in real-time.
- **Comprehensive Task Options**: Configure name, description, category, priority, custom color avatar, icon, and recurrence (daily, weekly, custom).
- **Search & Filtering**: Instant search by task name and filtering by category, priority, or archived status.

### 🔥 Streak System & Gamification
- **Automatic Streak Tracking**: Calculates current streak, longest streak, and daily completion consistency scores.
- **Gamification Badges**: Earn achievements like *Seedling*, *Sprout*, *Sapling*, *Ancient Oak*, *Perfect Week*, and *Habit Master*.
- **Consistency Scores**: Live productivity score updated on every task completion.

### 📊 Comprehensive Reports & Analytics
- **Interactive Reports Page**: Dedicated Weekly and Monthly analytical reports.
- **Heatmap & Trend Charts**: 365-day calendar activity heatmap and daily/weekly trend breakdown using Chart.js.
- **Automated Insights**: AI-style improvement suggestions based on best-performing and most-skipped habits.
- **Export Capabilities**: One-click **Print Report** and **Download Chart as PNG**.

### 🛡️ Separate Admin Console
- **Dedicated Admin Login**: Separate secure access at `/api/auth/admin/login`.
- **System Metrics & Analytics**: Platform-wide user metrics, system logs, categories manager, and announcements publisher.
- **Feature Flags & Modular Architecture**: Dynamically toggle modules (e.g., Expense Tracker, Pomodoro Timer, AI Coach) for easy future expansion.

### 🔔 Reminders & Automated Email Service
- **Browser Push Notifications**: Create customizable task reminders at specific times.
- **Automated Weekly Email Digest**: Sends HTML summaries directly to registered users with toggle switches in settings.

---

## 🛠️ Technology Stack

- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Vanilla CSS3 (CSS Variables, Flexbox, Grid, Glassmorphism), Chart.js, FontAwesome Icons, Google Fonts (Inter, Outfit).
- **Backend**: Python 3.13, Flask REST API, Werkzeug Security (Scrypt password hashing), PyJWT.
- **Database**: SQLite 3 with Foreign Key constraints and cascading deletes.

---

## 📁 Repository Structure

```
habitflow/
├── backend/
│   ├── admin.py               # Admin terminal API endpoints & feature flags
│   ├── app.py                 # Flask server initialization & routes
│   ├── auth.py                # JWT Authentication, session cookies & user registration
│   ├── database.py            # SQLite schema migrations & database initializer
│   ├── email_service.py       # Automated weekly email report engine
│   ├── habitflow.db           # SQLite database
│   ├── populate_db.py         # Demo data generator script
│   ├── reports.py             # Analytical reports calculations
│   ├── requirements.txt       # Python dependencies
│   ├── reset_passwords.py     # Password hashing & sync helper
│   ├── streaks.py             # Streaks & productivity score algorithms
│   ├── tasks.py               # Task CRUD & drag-and-drop reordering API
│   └── tests.py               # Backend automated integration tests
├── frontend/
│   ├── css/
│   │   └── styles.css         # Main stylesheet (themes, glassmorphism, responsive grid)
│   ├── js/
│   │   ├── api.js             # Fetch HTTP client wrapper & Toast notifications
│   │   └── app.js             # SPA routing, view loaders & event listeners
│   └── index.html             # Single Page Application HTML document
├── README.md                  # Project documentation
└── run.py                     # Entry point server script
```

---

## 🚀 Getting Started Locally

### Prerequisites
- **Python 3.10+** installed on your system.

### Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/shamimiem21-art/website.git
   cd website
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Initialize & Seed Database**:
   ```bash
   python backend/populate_db.py
   ```

4. **Run the Application**:
   ```bash
   python run.py
   ```

5. **Access the Web App**:
   Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 🔑 Demo Credentials

| Role | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Demo User** | `demo@habitflow.com` | `demopassword` | Full User Dashboard & Habits |
| **Administrator** | `admin@habitflow.com` | `adminpassword` | Elevated Admin Terminal |

*(Note: One-Click login buttons are also available on the login screen for instant demo access.)*

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
