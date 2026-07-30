/**
 * HABITFLOW CORE APPLICATION ENGINE
 * Single-Page Architecture with pre-seeded demonstration data.
 */

// Application State
const state = {
    user: null,
    theme: 'light',
    tasks: [],
    completions: {}, // { taskId_dateStr: true/false }
    categories: [
        { id: 1, name: 'Health & Fitness', color: '#4caf50', icon: 'heartbeat' },
        { id: 2, name: 'Mindfulness & Mental', color: '#8e24aa', icon: 'brain' },
        { id: 3, name: 'Productivity & Work', color: '#1e88e5', icon: 'briefcase' },
        { id: 4, name: 'Learning & Skills', color: '#fb8c00', icon: 'book' }
    ],
    announcements: [
        { id: 1, title: 'Welcome to HabitFlow 🌿', content: 'Track your growth daily with our nature-inspired tracker.', created_at: '2026-07-26' },
        { id: 2, title: 'Analytical Reports Updated 📊', content: 'Export your weekly and monthly summaries directly to PDF or print view.', created_at: '2026-07-30' }
    ],
    reminders: [],
    featureFlags: {
        ai_recommendations: true,
        community_challenges: true,
        dark_mode_customization: true,
        pdf_exports: true
    },
    systemLogs: [
        { id: 1, level: 'info', message: 'HabitFlow Engine initialized successfully.', created_at: '2026-07-31 01:00:00' },
        { id: 2, level: 'info', message: 'Pre-seeded demonstration habits loaded.', created_at: '2026-07-31 01:05:00' }
    ],
    reportType: 'weekly',
    reportOffset: 0
};

// Pre-seeded Demo Data Builder
function saveStateToLocalStorage() {
    try {
        const payload = {
            user: state.user,
            theme: state.theme,
            tasks: state.tasks,
            completions: state.completions,
            reminders: state.reminders,
            categories: state.categories,
            featureFlags: state.featureFlags
        };
        localStorage.setItem('habitflow_state', JSON.stringify(payload));
    } catch (e) {
        console.error('Error saving state:', e);
    }
}

function loadStateFromLocalStorage() {
    try {
        const saved = localStorage.getItem('habitflow_state');
        if (saved) {
            const data = JSON.parse(saved);
            if (data.user) state.user = data.user;
            if (data.theme) state.theme = data.theme;
            if (data.tasks && data.tasks.length > 0) state.tasks = data.tasks;
            if (data.completions && Object.keys(data.completions).length > 0) state.completions = data.completions;
            if (data.reminders) state.reminders = data.reminders;
            if (data.categories) state.categories = data.categories;
            if (data.featureFlags) state.featureFlags = data.featureFlags;
            return true;
        }
    } catch (e) {
        console.error('Error loading state:', e);
    }
    return false;
}

function seedInitialData() {
    const hasLoaded = loadStateFromLocalStorage();
    if (hasLoaded && state.tasks.length > 0) {
        return; // Retain user's custom tasks and completions across refreshes
    }

    const defaultTasks = [
        { id: 1, name: 'Morning Meditation (10 mins)', category: 'Mindfulness & Mental', color: '#8e24aa', icon: 'brain', priority: 'high', is_active: 1, is_archived: 0, order_idx: 1 },
        { id: 2, name: 'Drink 2.5 Liters of Water', category: 'Health & Fitness', color: '#4caf50', icon: 'tint', priority: 'high', is_active: 1, is_archived: 0, order_idx: 2 },
        { id: 3, name: 'Read 20 Pages of Book', category: 'Learning & Skills', color: '#fb8c00', icon: 'book', priority: 'medium', is_active: 1, is_archived: 0, order_idx: 3 },
        { id: 4, name: '30 Mins Daily Workout', category: 'Health & Fitness', color: '#e53935', icon: 'running', priority: 'high', is_active: 1, is_archived: 0, order_idx: 4 },
        { id: 5, name: 'Deep Work Session (90 mins)', category: 'Productivity & Work', color: '#1e88e5', icon: 'laptop-code', priority: 'medium', is_active: 1, is_archived: 0, order_idx: 5 },
        { id: 6, name: 'Night Journaling & Reflection', category: 'Mindfulness & Mental', color: '#3949ab', icon: 'pen-fancy', priority: 'low', is_active: 1, is_archived: 0, order_idx: 6 }
    ];

    state.tasks = defaultTasks;
    state.completions = {}; // Start clean with 0 tasks marked done

    saveStateToLocalStorage();
}

// Helper: Format Date YYYY-MM-DD
function formatDate(dateObj) {
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, '0');
    const d = String(dateObj.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// DOM Binding Helper
function bindEvent(id, event, handler) {
    const el = document.getElementById(id);
    if (el) el.addEventListener(event, handler);
}

// ONE-CLICK DEMO USER & ADMIN LOGINS
function quickDemoLogin() {
    state.user = { id: 101, name: 'Shamim Hossen (Demo User)', email: 'demo@habitflow.com', role: 'user' };
    showToast('Logged in as Demo User!', 'success');
    enterApp();
}

function quickAdminLogin() {
    state.user = { id: 1, name: 'System Administrator', email: 'admin@habitflow.com', role: 'admin' };
    showToast('Logged in to Admin Terminal!', 'success');
    enterApp();
}

window.quickDemoLogin = quickDemoLogin;
window.quickAdminLogin = quickAdminLogin;

// Navigation & Auth Flow
function switchAuthPane(paneName) {
    document.querySelectorAll('.auth-pane').forEach(p => p.classList.add('hidden'));
    const target = document.getElementById(`auth-${paneName}-pane`);
    if (target) target.classList.remove('hidden');
}

function enterApp() {
    saveStateToLocalStorage();
    const authContainer = document.getElementById('auth-container');
    const appContainer = document.getElementById('app-container');

    if (authContainer) {
        authContainer.classList.add('hidden');
        authContainer.style.setProperty('display', 'none', 'important');
    }
    if (appContainer) {
        appContainer.classList.remove('hidden');
        appContainer.style.setProperty('display', 'flex', 'important');
    }

    // Update Header & User Info
    document.getElementById('user-name-lbl').textContent = state.user.name;
    document.getElementById('user-role-lbl').textContent = state.user.role === 'admin' ? 'Administrator' : 'Explorer';
    document.getElementById('user-avatar-lbl').textContent = state.user.name.charAt(0).toUpperCase();

    // Show/Hide Admin Nav Item
    const adminNav = document.getElementById('nav-admin');
    if (adminNav) {
        if (state.user.role === 'admin') adminNav.classList.remove('hidden');
        else adminNav.classList.add('hidden');
    }

    const currentHash = window.location.hash.replace('#', '');
    const validViews = ['dashboard', 'tracker', 'stats', 'reports', 'calendar', 'profile', 'admin'];
    if (!validViews.includes(currentHash)) {
        window.location.hash = '#dashboard';
    }

    handleRouting();
}

function handleRouting() {
    let hash = window.location.hash.replace('#', '');
    const validViews = ['dashboard', 'tracker', 'stats', 'reports', 'calendar', 'profile', 'admin'];
    if (!validViews.includes(hash)) {
        hash = 'dashboard';
    }

    document.querySelectorAll('.view-section').forEach(s => s.classList.add('hidden'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const activeNav = document.querySelector(`.nav-item[data-view="${hash}"]`);
    if (activeNav) activeNav.classList.add('active');

    const activeSec = document.getElementById(`${hash}-view`);
    if (activeSec) activeSec.classList.remove('hidden');

    // Render section specifics
    if (hash === 'dashboard') renderDashboard();
    else if (hash === 'tracker') renderTracker();
    else if (hash === 'stats') renderStats();
    else if (hash === 'reports') renderReports();
    else if (hash === 'calendar') renderCalendar();
    else if (hash === 'profile') renderProfile();
    else if (hash === 'admin' && state.user.role === 'admin') renderAdmin();
}

// RENDER DASHBOARD
function renderDashboard() {
    document.getElementById('dashboard-greeting').textContent = `Hello, ${state.user.name.split(' ')[0]} 🌿`;
    
    // Calculate Streak & Metrics
    const metrics = calculateMetrics();
    document.getElementById('dashboard-score').textContent = metrics.score;
    document.getElementById('stat-current-streak').textContent = `${metrics.currentStreak} days`;
    document.getElementById('stat-longest-streak').textContent = `${metrics.longestStreak} days`;
    document.getElementById('stat-weekly-pct').textContent = `${metrics.weeklyPct}%`;
    document.getElementById('stat-monthly-pct').textContent = `${metrics.monthlyPct}%`;

    // Render Today's Habits Checklist
    renderDashboardTodayTasks();

    // Render Heatmap
    renderHeatmap();

    // Render Badges
    renderBadges(metrics);

    // Render Announcements
    renderDashboardAnnouncements();
}

function calculateMetrics() {
    const today = new Date();
    let currentStreak = 0;
    let longestStreak = 0;
    let tempStreak = 0;
    const activeTasks = state.tasks.filter(t => t.is_active && !t.is_archived);

    // Count total completions across all time
    let totalCompletedCount = 0;
    Object.values(state.completions).forEach(val => {
        if (val === 1) totalCompletedCount++;
    });

    // Calculate streak from past 60 days
    for (let i = 0; i < 60; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = formatDate(d);

        let completedTodayCount = 0;
        activeTasks.forEach(t => {
            if (state.completions[`${t.id}_${dateStr}`] === 1) completedTodayCount++;
        });

        if (activeTasks.length > 0 && completedTodayCount > 0) {
            tempStreak++;
            if (i === 0 || tempStreak === i + 1) currentStreak = tempStreak;
            if (tempStreak > longestStreak) longestStreak = tempStreak;
        } else {
            tempStreak = 0;
        }
    }

    // Dynamic Weekly % (Past 7 days)
    let weeklyCompleted = 0;
    let totalWeeklyPossible = activeTasks.length * 7;
    for (let i = 0; i < 7; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = formatDate(d);
        activeTasks.forEach(t => {
            if (state.completions[`${t.id}_${dateStr}`] === 1) weeklyCompleted++;
        });
    }
    const weeklyPct = totalWeeklyPossible > 0 ? Math.round((weeklyCompleted / totalWeeklyPossible) * 100) : 0;

    // Dynamic Monthly % (Past 30 days)
    let monthlyCompleted = 0;
    let totalMonthlyPossible = activeTasks.length * 30;
    for (let i = 0; i < 30; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = formatDate(d);
        activeTasks.forEach(t => {
            if (state.completions[`${t.id}_${dateStr}`] === 1) monthlyCompleted++;
        });
    }
    const monthlyPct = totalMonthlyPossible > 0 ? Math.round((monthlyCompleted / totalMonthlyPossible) * 100) : 0;

    // Productivity Score starts at ZERO and grows as user completes tasks
    const score = totalCompletedCount === 0 ? 0 : Math.round((currentStreak * 10) + (weeklyPct * 5) + (totalCompletedCount * 2));

    return { score, currentStreak, longestStreak, weeklyPct, monthlyPct, totalCompletedCount };
}

function renderDashboardTodayTasks() {
    const container = document.getElementById('dashboard-tasks-container');
    if (!container) return;

    const todayStr = formatDate(new Date());
    const activeTasks = state.tasks.filter(t => t.is_active && !t.is_archived);

    if (activeTasks.length === 0) {
        container.innerHTML = '<p class="text-muted">No habits added yet. Click "Add Habit" above!</p>';
        return;
    }

    container.innerHTML = activeTasks.map(t => {
        const isDone = state.completions[`${t.id}_${todayStr}`] === 1;
        return `
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px; border-bottom: 1px solid var(--border);">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <label class="habit-chk">
                        <input type="checkbox" ${isDone ? 'checked' : ''} onchange="toggleTaskToday(${t.id}, this.checked)">
                        <span class="chk-mark"></span>
                    </label>
                    <span style="font-weight: 600; text-decoration: ${isDone ? 'line-through' : 'none'}; opacity: ${isDone ? 0.6 : 1};">
                        <i class="fas fa-${t.icon}" style="color: ${t.color}; margin-right: 6px;"></i> ${t.name}
                    </span>
                </div>
                <span class="tag tag-priority-${t.priority}">${t.priority}</span>
            </div>
        `;
    }).join('');
}

function toggleTaskToday(taskId, isChecked) {
    const todayStr = formatDate(new Date());
    state.completions[`${taskId}_${todayStr}`] = isChecked ? 1 : 0;
    saveStateToLocalStorage();
    showToast(isChecked ? 'Habit completed!' : 'Habit unchecked', isChecked ? 'success' : 'info');
    renderDashboard();
}

function renderHeatmap() {
    const grid = document.getElementById('heatmap-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const today = new Date();
    for (let i = 180; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = formatDate(d);

        let count = 0;
        state.tasks.forEach(t => {
            if (state.completions[`${t.id}_${dateStr}`] === 1) count++;
        });

        const level = count === 0 ? 0 : count <= 2 ? 1 : count <= 4 ? 2 : count <= 5 ? 3 : 4;
        const cell = document.createElement('div');
        cell.className = `cell level-${level}`;
        cell.title = `${dateStr}: ${count} habits completed`;
        grid.appendChild(cell);
    }
}

function renderBadges(metrics) {
    const container = document.getElementById('badges-container');
    if (!container) return;

    const badges = [
        { name: 'Seedling', icon: 'seedling', unlocked: metrics.totalCompletedCount > 0, desc: 'Completed 1st habit' },
        { name: '7-Day Streak', icon: 'fire', unlocked: metrics.currentStreak >= 7, desc: '7 days consistent' },
        { name: 'Master Flow', icon: 'trophy', unlocked: metrics.longestStreak >= 14, desc: '14+ days streak' },
        { name: 'Consistency Hero', icon: 'star', unlocked: metrics.weeklyPct >= 80, desc: '80%+ weekly progress' }
    ];

    container.innerHTML = badges.map(b => `
        <div class="badge-item" style="opacity: ${b.unlocked ? 1 : 0.4};">
            <div class="badge-icon" style="background: ${b.unlocked ? 'var(--primary-light)' : 'rgba(0,0,0,0.05)'}; color: ${b.unlocked ? 'var(--primary)' : 'var(--text-light)'};"><i class="fas fa-${b.icon}"></i></div>
            <div>
                <strong>${b.name} ${b.unlocked ? '✓' : '🔒'}</strong>
                <p style="font-size: 11px; color: var(--text-muted);">${b.desc}</p>
            </div>
        </div>
    `).join('');
}

function renderDashboardAnnouncements() {
    const container = document.getElementById('dashboard-announcements-list');
    if (!container) return;

    container.innerHTML = state.announcements.map(a => `
        <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">
            <strong style="color: var(--primary); font-size: 14px;">${a.title}</strong>
            <p style="font-size: 13px; color: var(--text-muted); margin-top: 2px;">${a.content}</p>
            <span style="font-size: 11px; color: var(--text-light);">${a.created_at}</span>
        </div>
    `).join('');
}

// RENDER TASK TRACKER MATRIX
function renderTracker() {
    const tbody = document.getElementById('tracker-tbody');
    if (!tbody) return;

    // Populate category filter dropdown
    const catSelect = document.getElementById('filter-category');
    if (catSelect) {
        catSelect.innerHTML = '<option value="">All Categories</option>' + 
            state.categories.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
    }

    const today = new Date();
    // Generate dates for current week (Sun - Sat)
    const weekDates = [];
    const currentDay = today.getDay(); // 0 = Sun
    for (let i = 0; i < 7; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() - currentDay + i);
        weekDates.push(formatDate(d));
    }

    const activeTasks = state.tasks.filter(t => t.is_active && !t.is_archived);

    tbody.innerHTML = activeTasks.map(t => {
        let doneWeekCount = 0;
        const weekCheckboxes = weekDates.map(dStr => {
            const isDone = state.completions[`${t.id}_${dStr}`] === 1;
            if (isDone) doneWeekCount++;
            return `
                <td style="text-align: center;">
                    <label class="habit-chk">
                        <input type="checkbox" ${isDone ? 'checked' : ''} onchange="toggleTaskMatrix(${t.id}, '${dStr}', this.checked)">
                        <span class="chk-mark"></span>
                    </label>
                </td>
            `;
        }).join('');

        const pct = Math.round((doneWeekCount / 7) * 100);

        return `
            <tr draggable="true" ondragstart="handleDragStart(event, ${t.id})" ondragover="handleDragOver(event)" ondrop="handleDrop(event, ${t.id})">
                <td><i class="fas fa-grip-vertical text-muted" style="cursor: grab;"></i></td>
                <td>
                    <strong style="color: var(--text);"><i class="fas fa-${t.icon}" style="color: ${t.color}; margin-right: 6px;"></i> ${t.name}</strong>
                </td>
                <td><span class="tag" style="background: ${t.color}22; color: ${t.color};">${t.category}</span></td>
                ${weekCheckboxes}
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: ${pct}%;"></div></div>
                        <span style="font-size: 12px; font-weight: 600;">${pct}%</span>
                    </div>
                </td>
                <td>
                    <button class="btn-icon" onclick="editTask(${t.id})" title="Edit"><i class="fas fa-edit"></i></button>
                    <button class="btn-icon text-danger" onclick="deleteTask(${t.id})" title="Delete"><i class="fas fa-trash"></i></button>
                </td>
            </tr>
        `;
    }).join('');
}

function toggleTaskMatrix(taskId, dateStr, isChecked) {
    state.completions[`${taskId}_${dateStr}`] = isChecked ? 1 : 0;
    saveStateToLocalStorage();
    renderTracker();
}

// DRAG AND DROP REORDERING
let draggedTaskId = null;
function handleDragStart(e, taskId) {
    draggedTaskId = taskId;
}
function handleDragOver(e) {
    e.preventDefault();
}
function handleDrop(e, targetTaskId) {
    e.preventDefault();
    if (draggedTaskId === targetTaskId) return;
    const draggedIdx = state.tasks.findIndex(t => t.id === draggedTaskId);
    const targetIdx = state.tasks.findIndex(t => t.id === targetTaskId);
    const [moved] = state.tasks.splice(draggedIdx, 1);
    state.tasks.splice(targetIdx, 0, moved);
    saveStateToLocalStorage();
    renderTracker();
    showToast('Task order updated!', 'info');
}

// RENDER CHARTS
function renderStats() {
    const dailyCtx = document.getElementById('chart-daily');
    const categoryCtx = document.getElementById('chart-category');
    const weeklyTrendCtx = document.getElementById('chart-weekly-trend');

    if (!dailyCtx || !categoryCtx || !weeklyTrendCtx) return;

    // Daily Completion Chart
    new Chart(dailyCtx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Completion Rate (%)',
                data: [85, 90, 75, 95, 80, 70, 88],
                borderColor: '#2e7d32',
                backgroundColor: 'rgba(46, 125, 50, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    // Category Distribution
    new Chart(categoryCtx, {
        type: 'doughnut',
        data: {
            labels: state.categories.map(c => c.name),
            datasets: [{
                data: [30, 25, 25, 20],
                backgroundColor: ['#4caf50', '#8e24aa', '#1e88e5', '#fb8c00']
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    // Weekly Trend Analysis
    new Chart(weeklyTrendCtx, {
        type: 'bar',
        data: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            datasets: [{
                label: 'Habits Completed',
                data: [38, 42, 40, 45],
                backgroundColor: '#2e7d32'
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

// RENDER REPORTS
function renderReports() {
    const container = document.getElementById('reports-content-container');
    if (!container) return;

    const metrics = calculateMetrics();
    const ratePct = state.reportType === 'weekly' ? metrics.weeklyPct : metrics.monthlyPct;

    container.innerHTML = `
        <div class="glass-card" style="margin-bottom: 20px;">
            <h3>📊 Executive Performance Report (${state.reportType.toUpperCase()})</h3>
            <p class="text-muted">Generated for: <strong>${state.user.name}</strong></p>
            
            <div class="metrics-grid" style="margin-top: 20px;">
                <div class="metric-card">
                    <div class="metric-details">
                        <span class="metric-value">${ratePct}%</span>
                        <span class="metric-label">Average Consistency Rate</span>
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-details">
                        <span class="metric-value">${metrics.totalCompletedCount}</span>
                        <span class="metric-label">Total Completed Tasks</span>
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-details">
                        <span class="metric-value">${metrics.totalCompletedCount > 0 ? 'Active Habits' : 'No Data Yet'}</span>
                        <span class="metric-label">Top Performing Category</span>
                    </div>
                </div>
            </div>

            <h4 style="margin-top: 24px;">💡 Growth & Improvement Suggestions</h4>
            <ul style="margin-top: 10px; padding-left: 20px; color: var(--text-muted); line-height: 1.6;">
                ${metrics.totalCompletedCount === 0 ? 
                    '<li>You have not checked off any habits yet! Check off your first habit on the dashboard or tracker to begin building your streak! 🌿</li>' : 
                    `<li>You have completed <strong>${metrics.totalCompletedCount}</strong> habit task(s) so far. Outstanding momentum!</li>
                     <li>Your current streak is <strong>${metrics.currentStreak} day(s)</strong> and longest streak is <strong>${metrics.longestStreak} day(s)</strong>.</li>`
                }
            </ul>
        </div>
    `;
}
}

// RENDER CALENDAR
function renderCalendar() {
    const grid = document.getElementById('calendar-days-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const daysInMonth = 31;
    for (let i = 1; i <= daysInMonth; i++) {
        const cell = document.createElement('div');
        cell.className = 'cal-day-cell';
        cell.innerHTML = `
            <div class="cal-day-num">${i}</div>
            <div class="cal-day-dots">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        `;
        cell.onclick = () => {
            document.getElementById('cal-day-modal-date').textContent = `July ${i}, 2026 Details`;
            document.getElementById('cal-day-modal-body').innerHTML = '<p>Daily summary: 5 out of 6 habits completed successfully. 🌿</p>';
            document.getElementById('calendar-day-modal').classList.remove('hidden');
        };
        grid.appendChild(cell);
    }
}

// RENDER PROFILE & REMINDERS
function renderProfile() {
    document.getElementById('profile-name-lbl').textContent = state.user.name;
    document.getElementById('profile-email-lbl').textContent = state.user.email;
    document.getElementById('profile-avatar-lbl').textContent = state.user.name.charAt(0).toUpperCase();
    document.getElementById('profile-name-input').value = state.user.name;

    // Populate task select for reminders
    const taskSelect = document.getElementById('reminder-task-select');
    if (taskSelect) {
        taskSelect.innerHTML = '<option value="">Select Task...</option>' + 
            state.tasks.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
    }

    renderRemindersList();
}

function renderRemindersList() {
    const container = document.getElementById('reminder-list-container');
    if (!container) return;

    if (state.reminders.length === 0) {
        container.innerHTML = '<p class="text-muted" style="font-size: 13px;">No custom reminders set yet.</p>';
        return;
    }

    container.innerHTML = state.reminders.map((r, idx) => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid var(--border);">
            <span><i class="fas fa-bell" style="color: var(--primary);"></i> ${r.taskName} at <strong>${r.time}</strong></span>
            <button class="btn-icon text-danger" onclick="deleteReminder(${idx})"><i class="fas fa-trash"></i></button>
        </div>
    `).join('');
}

function deleteReminder(idx) {
    state.reminders.splice(idx, 1);
    renderRemindersList();
    showToast('Reminder removed', 'info');
}

// RENDER ADMIN PANEL
function renderAdmin() {
    const usersTbody = document.getElementById('admin-users-tbody');
    if (usersTbody) {
        const demoUsers = [
            { id: 1, name: 'System Administrator', email: 'admin@habitflow.com', role: 'admin', is_active: 1 },
            { id: 101, name: 'Shamim Hossen (Demo User)', email: 'demo@habitflow.com', role: 'user', is_active: 1 },
            { id: 102, name: 'Alex Rivera', email: 'alex@domain.com', role: 'user', is_active: 1 }
        ];

        usersTbody.innerHTML = demoUsers.map(u => `
            <tr>
                <td>#${u.id}</td>
                <td><strong>${u.name}</strong></td>
                <td>${u.email}</td>
                <td><span class="tag tag-admin">${u.role}</span></td>
                <td><span style="color: #4caf50; font-weight: 600;">Active</span></td>
                <td>
                    <button class="btn-icon" title="Reset Password" onclick="showToast('Password reset email dispatched to ${u.email}', 'info')"><i class="fas fa-key"></i></button>
                </td>
            </tr>
        `).join('');
    }

    // Categories list
    const catsList = document.getElementById('admin-cats-list');
    if (catsList) {
        catsList.innerHTML = state.categories.map(c => `
            <li style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid var(--border);">
                <span><i class="fas fa-${c.icon}" style="color: ${c.color};"></i> ${c.name}</span>
                <span class="tag" style="background: ${c.color}22; color: ${c.color};">${c.color}</span>
            </li>
        `).join('');
    }

    // Feature Flags
    const flagsContainer = document.getElementById('admin-flags-container');
    if (flagsContainer) {
        flagsContainer.innerHTML = Object.keys(state.featureFlags).map(key => `
            <div class="setting-item" style="padding: 10px 0; border-bottom: 1px solid var(--border);">
                <div>
                    <strong>${key.replace('_', ' ').toUpperCase()}</strong>
                </div>
                <label class="switch">
                    <input type="checkbox" ${state.featureFlags[key] ? 'checked' : ''} onchange="state.featureFlags['${key}'] = this.checked; showToast('Feature flag updated', 'success');">
                    <span class="slider"></span>
                </label>
            </div>
        `).join('');
    }

    // System Logs
    const logsList = document.getElementById('admin-logs-list');
    if (logsList) {
        logsList.innerHTML = state.systemLogs.map(l => `
            <li style="font-size: 13px; padding: 6px 0; border-bottom: 1px solid var(--border);">
                <span style="color: var(--text-light);">${l.created_at}</span> [${l.level.toUpperCase()}]: ${l.message}
            </li>
        `).join('');
    }
}

// MODAL OPEN / EDIT / ADD HANDLERS
function openTaskModal() {
    document.getElementById('task-id').value = '';
    document.getElementById('task-name').value = '';
    document.getElementById('task-desc').value = '';
    document.getElementById('task-modal-title').textContent = 'Add New Habit / Task';

    const catSelect = document.getElementById('task-category');
    if (catSelect) {
        catSelect.innerHTML = state.categories.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
    }

    document.getElementById('task-modal').classList.remove('hidden');
}

function editTask(id) {
    const task = state.tasks.find(t => t.id === id);
    if (!task) return;

    openTaskModal();
    document.getElementById('task-id').value = task.id;
    document.getElementById('task-name').value = task.name;
    document.getElementById('task-desc').value = task.description || '';
    document.getElementById('task-category').value = task.category;
    document.getElementById('task-priority').value = task.priority;
    document.getElementById('task-modal-title').textContent = 'Edit Habit';
}

function deleteTask(id) {
    if (confirm('Are you sure you want to delete this habit?')) {
        state.tasks = state.tasks.filter(t => t.id !== id);
        saveStateToLocalStorage();
        renderTracker();
        showToast('Habit deleted', 'info');
    }
}

// INITIALIZATION & EVENT LISTENERS
document.addEventListener('DOMContentLoaded', () => {
    seedInitialData();

    // Theme Toggle
    bindEvent('theme-toggle-btn', 'click', () => {
        state.theme = state.theme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', state.theme);
        const icon = document.querySelector('#theme-toggle-btn i');
        if (icon) icon.className = state.theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        saveStateToLocalStorage();
    });

    // Auth Navigation
    bindEvent('goto-register', 'click', (e) => { e.preventDefault(); switchAuthPane('register'); });
    bindEvent('goto-login', 'click', (e) => { e.preventDefault(); switchAuthPane('login'); });
    bindEvent('goto-forgot-pw', 'click', (e) => { e.preventDefault(); switchAuthPane('forgot'); });
    bindEvent('forgot-cancel', 'click', (e) => { e.preventDefault(); switchAuthPane('login'); });
    bindEvent('goto-admin-login', 'click', (e) => { e.preventDefault(); switchAuthPane('admin'); });
    bindEvent('goto-user-login', 'click', (e) => { e.preventDefault(); switchAuthPane('login'); });

    // Auth Form Submit Handlers
    bindEvent('demo-user-btn', 'click', quickDemoLogin);
    bindEvent('demo-admin-btn', 'click', quickAdminLogin);

    bindEvent('login-form', 'submit', (e) => {
        e.preventDefault();
        const inputVal = document.getElementById('login-email').value.trim();
        const email = inputVal || 'demo@habitflow.com';
        state.user = { id: 101, name: email.split('@')[0], email: email, role: 'user' };
        showToast('Login successful!', 'success');
        enterApp();
    });

    bindEvent('register-form', 'submit', (e) => {
        e.preventDefault();
        const nameVal = document.getElementById('reg-name').value.trim() || 'Explorer';
        const emailVal = document.getElementById('reg-email').value.trim() || 'user@domain.com';
        state.user = { id: 201, name: nameVal, email: emailVal, role: 'user' };
        showToast('Account created successfully!', 'success');
        enterApp();
    });

    bindEvent('forgot-form', 'submit', (e) => {
        e.preventDefault();
        showToast('Password reset successfully. Please log in.', 'success');
        switchAuthPane('login');
    });

    bindEvent('admin-login-form', 'submit', (e) => {
        e.preventDefault();
        state.user = { id: 1, name: 'System Administrator', email: 'admin@habitflow.com', role: 'admin' };
        showToast('Admin verification successful!', 'success');
        enterApp();
    });

    // Logout
    bindEvent('logout-btn', 'click', () => {
        state.user = null;
        saveStateToLocalStorage();
        const authContainer = document.getElementById('auth-container');
        const appContainer = document.getElementById('app-container');

        if (appContainer) {
            appContainer.classList.add('hidden');
            appContainer.style.setProperty('display', 'none', 'important');
        }
        if (authContainer) {
            authContainer.classList.remove('hidden');
            authContainer.style.setProperty('display', 'flex', 'important');
        }

        switchAuthPane('login');
        showToast('Logged out', 'info');
    });

    // Hash Change Routing
    window.addEventListener('hashchange', handleRouting);

    // Open Add Task Modal
    bindEvent('open-add-task-btn', 'click', openTaskModal);
    bindEvent('task-modal-close', 'click', () => document.getElementById('task-modal').classList.add('hidden'));
    bindEvent('task-modal-cancel', 'click', () => document.getElementById('task-modal').classList.add('hidden'));

    // Task Form Submit
    bindEvent('task-form', 'submit', (e) => {
        e.preventDefault();
        const idVal = document.getElementById('task-id').value;
        const name = document.getElementById('task-name').value;
        const desc = document.getElementById('task-desc').value;
        const cat = document.getElementById('task-category').value;
        const priority = document.getElementById('task-priority').value;

        if (idVal) {
            const task = state.tasks.find(t => t.id === parseInt(idVal));
            if (task) {
                task.name = name;
                task.description = desc;
                task.category = cat;
                task.priority = priority;
                showToast('Habit updated!', 'success');
            }
        } else {
            const newTask = {
                id: Date.now(),
                name: name,
                description: desc,
                category: cat,
                color: '#4caf50',
                icon: 'check',
                priority: priority,
                is_active: 1,
                is_archived: 0,
                order_idx: state.tasks.length + 1
            };
            state.tasks.push(newTask);
            showToast('New habit created!', 'success');
        }

        saveStateToLocalStorage();
        document.getElementById('task-modal').classList.add('hidden');
        renderTracker();
        renderDashboard();
    });

    // Profile Updates
    bindEvent('profile-info-form', 'submit', (e) => {
        e.preventDefault();
        const newName = document.getElementById('profile-name-input').value;
        state.user.name = newName;
        document.getElementById('user-name-lbl').textContent = newName;
        document.getElementById('user-avatar-lbl').textContent = newName.charAt(0).toUpperCase();
        document.getElementById('profile-name-lbl').textContent = newName;
        saveStateToLocalStorage();
        showToast('Profile updated!', 'success');
    });

    // Add Reminder
    bindEvent('add-reminder-form', 'submit', (e) => {
        e.preventDefault();
        const taskId = document.getElementById('reminder-task-select').value;
        const time = document.getElementById('reminder-time-input').value;
        const task = state.tasks.find(t => t.id === parseInt(taskId));

        if (task && time) {
            state.reminders.push({ taskId: task.id, taskName: task.name, time });
            saveStateToLocalStorage();
            renderRemindersList();
            showToast(`Reminder set for ${task.name} at ${time}`, 'success');
        }
    });

    // Print & Download Buttons
    bindEvent('print-report-btn', 'click', () => window.print());
    bindEvent('download-chart-btn', 'click', () => showToast('Chart downloaded as PNG!', 'success'));

    // Mobile Navigation
    bindEvent('mobile-open-nav', 'click', () => document.querySelector('.app-wrapper').classList.add('mobile-open'));
    bindEvent('mobile-close-nav', 'click', () => document.querySelector('.app-wrapper').classList.remove('mobile-open'));

    // Auto-login if session exists in localStorage
    if (state.user) {
        enterApp();
    } else {
        const authContainer = document.getElementById('auth-container');
        const appContainer = document.getElementById('app-container');

        if (appContainer) {
            appContainer.classList.add('hidden');
            appContainer.style.setProperty('display', 'none', 'important');
        }
        if (authContainer) {
            authContainer.classList.remove('hidden');
            authContainer.style.setProperty('display', 'flex', 'important');
        }

        switchAuthPane('login');
    }
});
