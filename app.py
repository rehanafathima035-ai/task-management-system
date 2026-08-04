from flask import Flask, render_template, request, redirect, session
import sqlite3

import os

print(os.getcwd())

def init_db():
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'database.db'))
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            group_id INTEGER,
            title TEXT,
            description TEXT,
            due_date TEXT,
            status TEXT
        );
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            leader_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            user_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            title TEXT,
            is_completed BOOLEAN DEFAULT 0
        );
    ''')

    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = 'super_secret_todolist_key'  # Needed for session management
init_db()
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            print("Received:", username, password)

            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()

            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()

            print("Inserted into DB ✅")

            return redirect('/login')

        except Exception as e:
            print("Error:", e)
            return "Error occurred"

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        print("Received:", username, password)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Invalid Credentials. Please try again.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html', username=session['username'])

@app.route('/users')
def view_users():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    conn.close()

    return str(users)

# --- PERSONAL MODE ROUTES ---
@app.route('/personal')
def personal():
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Import datetime at the top of the logic if needed or just do it inline
    from datetime import datetime, timedelta
    
    # Check for upcoming reminders (due within 7 days)
    today_str = datetime.now().strftime('%Y-%m-%d')
    next_week_str = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute("SELECT id, title, due_date FROM tasks WHERE user_id=? AND status='Pending' AND due_date <= ?", (session['user_id'], next_week_str))
    reminders = cursor.fetchall()
    
    cursor.execute("SELECT id, title, description, due_date, status FROM tasks WHERE user_id=? AND group_id IS NULL ORDER BY due_date ASC", (session['user_id'],))
    tasks = cursor.fetchall()
    
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t[4] == 'Completed')
    
    cursor.execute("""
        SELECT s.id, s.task_id, s.title, s.is_completed 
        FROM subtasks s
        JOIN tasks t ON s.task_id = t.id
        WHERE t.user_id=? AND t.group_id IS NULL
    """, (session['user_id'],))
    all_subtasks = cursor.fetchall()
    subtasks_dict = {}
    for st in all_subtasks:
        subtasks_dict.setdefault(st[1], []).append(st)
        
    conn.close()
    
    return render_template('personal.html', tasks=tasks, reminders=reminders, username=session['username'], total_tasks=total_tasks, completed_tasks=completed_tasks, subtasks=subtasks_dict)

@app.route('/personal/add', methods=['POST'])
def add_personal_task():
    if 'user_id' not in session:
        return redirect('/login')
    
    title = request.form.get('title')
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, title, description, due_date, status) VALUES (?, ?, ?, ?, 'Pending')", 
                   (session['user_id'], title, description, due_date))
    conn.commit()
    conn.close()
    
    return redirect('/personal')

@app.route('/personal/edit/<int:task_id>', methods=['POST'])
def edit_personal_task(task_id):
    if 'user_id' not in session:
        return redirect('/login')
        
    title = request.form.get('title')
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET title=?, description=?, due_date=? WHERE id=? AND user_id=?", 
                   (title, description, due_date, task_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return redirect('/personal')

@app.route('/personal/delete/<int:task_id>')
def delete_personal_task(task_id):
    if 'user_id' not in session:
        return redirect('/login')
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return redirect('/personal')
    
@app.route('/personal/status/<int:task_id>')
def toggle_status(task_id):
    if 'user_id' not in session:
        return redirect('/login')
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM tasks WHERE id=? AND user_id=?", (task_id, session['user_id']))
    task = cursor.fetchone()
    
    if task:
        new_status = 'Completed' if task[0] == 'Pending' else 'Pending'
        cursor.execute("UPDATE tasks SET status=? WHERE id=? AND user_id=?", (new_status, task_id, session['user_id']))
        conn.commit()
    conn.close()
    
    return redirect('/personal')
    return redirect('/personal')

# --- PROFESSIONAL MODE ROUTES ---
@app.route('/professional')
def professional():
    if 'user_id' not in session: return redirect('/login')
    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM groups WHERE leader_id=?", (user_id,))
    led_groups = cursor.fetchall()
    
    cursor.execute('''
        SELECT g.id, g.name, u.username as leader_name 
        FROM groups g 
        JOIN group_members gm ON g.id = gm.group_id 
        JOIN users u ON g.leader_id = u.id
        WHERE gm.user_id=? AND g.leader_id != ?
    ''', (user_id, user_id))
    member_groups = cursor.fetchall()
    conn.close()
    return render_template('professional.html', username=session['username'], led_groups=led_groups, member_groups=member_groups)

@app.route('/professional/create_group', methods=['POST'])
def create_group():
    if 'user_id' not in session: return redirect('/login')
    name = request.form.get('name')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO groups (name, leader_id) VALUES (?, ?)", (name, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/professional')
    
@app.route('/professional/group/<int:group_id>')
def view_group(group_id):
    if 'user_id' not in session: return redirect('/login')
    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM groups WHERE id=?", (group_id,))
    group = cursor.fetchone()
    
    if not group: 
        conn.close()
        return redirect('/professional')
        
    is_leader = (group[2] == user_id)
    
    cursor.execute("SELECT * FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
    is_member = (cursor.fetchone() is not None)
    
    if not is_leader and not is_member:
        conn.close()
        return redirect('/professional')
    
    cursor.execute('''
        SELECT u.id, u.username 
        FROM users u 
        JOIN group_members gm ON u.id = gm.user_id 
        WHERE gm.group_id = ?
    ''', (group_id,))
    members = cursor.fetchall()
    
    cursor.execute('''
        SELECT t.id, t.title, t.description, t.due_date, t.status, u.username, t.user_id 
        FROM tasks t 
        LEFT JOIN users u ON t.user_id = u.id 
        WHERE t.group_id = ?
        ORDER BY t.due_date ASC
    ''', (group_id,))
    tasks = cursor.fetchall()
    
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t[4] == 'Completed')
    
    cursor.execute("""
        SELECT s.id, s.task_id, s.title, s.is_completed 
        FROM subtasks s
        JOIN tasks t ON s.task_id = t.id
        WHERE t.group_id=?
    """, (group_id,))
    all_subtasks = cursor.fetchall()
    subtasks_dict = {}
    for st in all_subtasks:
        subtasks_dict.setdefault(st[1], []).append(st)
    
    conn.close()
    return render_template('group.html', username=session['username'], user_id=user_id, group=group, is_leader=is_leader, members=members, tasks=tasks, total_tasks=total_tasks, completed_tasks=completed_tasks, subtasks=subtasks_dict)
    
@app.route('/professional/group/<int:group_id>/add_member', methods=['POST'])
def add_group_member(group_id):
    if 'user_id' not in session: return redirect('/login')
    member_username = request.form.get('username')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username=?", (member_username,))
    user = cursor.fetchone()
    if user:
        cursor.execute("SELECT * FROM group_members WHERE group_id=? AND user_id=?", (group_id, user[0]))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (group_id, user[0]))
            conn.commit()
    conn.close()
    return redirect(f'/professional/group/{group_id}')
    
@app.route('/professional/group/<int:group_id>/assign_task', methods=['POST'])
def assign_group_task(group_id):
    if 'user_id' not in session: return redirect('/login')
    title = request.form.get('title')
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    assign_to = request.form.get('assign_to') # user_id
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (group_id, user_id, title, description, due_date, status) VALUES (?, ?, ?, ?, ?, 'Pending')",
                   (group_id, assign_to, title, description, due_date))
    conn.commit()
    conn.close()
    return redirect(f'/professional/group/{group_id}')

@app.route('/professional/group/<int:group_id>/status/<int:task_id>')
def toggle_group_task_status(group_id, task_id):
    if 'user_id' not in session: return redirect('/login')
    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT status, user_id FROM tasks WHERE id=? AND group_id=?", (task_id, group_id))
    task = cursor.fetchone()
    
    if task:
        cursor.execute("SELECT leader_id FROM groups WHERE id=?", (group_id,))
        group = cursor.fetchone()
        # Only leader or the assigned user can toggle status
        if task[1] == user_id or (group and group[0] == user_id):
            new_status = 'Completed' if task[0] == 'Pending' else 'Pending'
            cursor.execute("UPDATE tasks SET status=? WHERE id=? AND group_id=?", (new_status, task_id, group_id))
            conn.commit()
    conn.close()
    return redirect(f'/professional/group/{group_id}')

@app.route('/professional/group/<int:group_id>/remove_member/<int:member_id>')
def remove_group_member(group_id, member_id):
    if 'user_id' not in session: return redirect('/login')
    # Validate leader
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT leader_id FROM groups WHERE id=?", (group_id,))
    group = cursor.fetchone()
    if group and group[0] == session['user_id']:
        cursor.execute("DELETE FROM group_members WHERE group_id=? AND user_id=?", (group_id, member_id))
        conn.commit()
    conn.close()
    return redirect(f'/professional/group/{group_id}')

@app.route('/professional/group/<int:group_id>/edit_task/<int:task_id>', methods=['POST'])
def edit_group_task(group_id, task_id):
    if 'user_id' not in session: return redirect('/login')
    
    title = request.form.get('title')
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    assign_to = request.form.get('assign_to')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT leader_id FROM groups WHERE id=?", (group_id,))
    group = cursor.fetchone()
    if group and group[0] == session['user_id']:
        cursor.execute("UPDATE tasks SET title=?, description=?, due_date=?, user_id=? WHERE id=? AND group_id=?",
                       (title, description, due_date, assign_to, task_id, group_id))
        conn.commit()
    conn.close()
    return redirect(f'/professional/group/{group_id}')

@app.route('/professional/group/<int:group_id>/delete_task/<int:task_id>')
def delete_group_task(group_id, task_id):
    if 'user_id' not in session: return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT leader_id FROM groups WHERE id=?", (group_id,))
    group = cursor.fetchone()
    if group and group[0] == session['user_id']:
        cursor.execute("DELETE FROM tasks WHERE id=? AND group_id=?", (task_id, group_id))
    return redirect(f'/professional/group/{group_id}')

# --- SUBTASK ROUTES ---
@app.route('/task/<int:task_id>/add_subtask', methods=['POST'])
def add_subtask(task_id):
    if 'user_id' not in session: return redirect('/login')
    title = request.form.get('title')
    source = request.form.get('source') # 'personal' or 'group_<id>'
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO subtasks (task_id, title) VALUES (?, ?)", (task_id, title))
    conn.commit()
    conn.close()
    
    if source == 'personal':
        return redirect('/personal')
    elif source and source.startswith('group_'):
        group_id = source.split('_')[1]
        return redirect(f'/professional/group/{group_id}')
    return redirect('/dashboard')

@app.route('/subtask/<int:subtask_id>/toggle')
def toggle_subtask(subtask_id):
    if 'user_id' not in session: return redirect('/login')
    source = request.args.get('source', 'personal')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT is_completed FROM subtasks WHERE id=?", (subtask_id,))
    subtask = cursor.fetchone()
    if subtask:
        new_status = 0 if subtask[0] else 1
        cursor.execute("UPDATE subtasks SET is_completed=? WHERE id=?", (new_status, subtask_id))
        conn.commit()
    conn.close()
    
    if source == 'personal':
        return redirect('/personal')
    elif source and source.startswith('group_'):
        group_id = source.split('_')[1]
        return redirect(f'/professional/group/{group_id}')
    return redirect('/dashboard')

@app.route('/subtask/<int:subtask_id>/delete')
def delete_subtask(subtask_id):
    if 'user_id' not in session: return redirect('/login')
    source = request.args.get('source', 'personal')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subtasks WHERE id=?", (subtask_id,))
    conn.commit()
    conn.close()
    
    if source == 'personal':
        return redirect('/personal')
    elif source and source.startswith('group_'):
        group_id = source.split('_')[1]
        return redirect(f'/professional/group/{group_id}')
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(debug=True)