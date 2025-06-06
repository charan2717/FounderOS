from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'founder_secret_key'

DB_PATH = 'users.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize tables
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    try:
      c.execute("ALTER TABLE posts ADD COLUMN image_path TEXT")
      print("image_path column added successfully.")
    except sqlite3.OperationalError as e:
      if "duplicate column name" in str(e).lower():
        print("Column already exists.")
      else:
        raise
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')

    # Community Posts
    c.execute('''
      CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        role TEXT,
        content TEXT,
        image_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
    #investors
    c.execute('''
        CREATE TABLE IF NOT EXISTS investors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT,
            email TEXT,
            password TEXT,
            bio TEXT
        );
    ''')

# Comments
    c.execute('''
      CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        username TEXT,
        content TEXT,
        image_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Replies
    c.execute('''
      CREATE TABLE IF NOT EXISTS replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comment_id INTEGER,
        username TEXT,
        content TEXT,
        image_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')


    # News (admin updates)
    c.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Projects (for founder)
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            founder_username TEXT,
            project_name TEXT,
            project_desc TEXT
        )
    ''')

    # Team members (for founder)
    c.execute('''
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            founder_username TEXT,
            member_name TEXT,
            member_role TEXT
        )
    ''')

    # Goals (for founder)
    c.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            founder_username TEXT,
            goal_desc TEXT,
            completed INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

# Seed admin user if missing
def seed_admin():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role='admin'")
    if not c.fetchone():
        # WARNING: Store hashed passwords in production!
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin123', 'admin'))
    conn.commit()
    conn.close()

init_db()
seed_admin()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role'].lower()

        if role == 'admin':
            return "Cannot signup as admin", 403

        conn = get_db_connection()
        c = conn.cursor()
        try:
            # Insert into users table
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
            
            # Also insert into investors table if role is investor
            if role == 'investor':
                c.execute("INSERT INTO investors (username, password) VALUES (?, ?)", (username, password))

            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists", 409
        finally:
            conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role'].lower()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=? AND role=?", (username, password, role))
        user = c.fetchone()
        conn.close()

        if user:
            session['username'] = user['username']
            session['role'] = user['role']

            if role == 'admin':
                return redirect(url_for('admin_home'))
            elif role == 'founder':
                return redirect(url_for('founder_home'))
            elif role == 'investor':
                return redirect(url_for('investor_home'))
        else:
            return "Invalid credentials or role mismatch", 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ----------------- Admin routes --------------------

@app.route('/admin/home')
def admin_home():
    if 'role' in session and session['role'] == 'admin':
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM news ORDER BY created_at DESC")
        news_items = c.fetchall()
        conn.close()
        return render_template('admin_home.html', user=session['username'], news_items=news_items)
    return redirect(url_for('login'))

@app.route('/admin/news/add', methods=['POST'])
def admin_add_news():
    if 'role' in session and session['role'] == 'admin':
        title = request.form['title']
        content = request.form['content']
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO news (title, content) VALUES (?, ?)", (title, content))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_home'))
    return redirect(url_for('login'))

from flask import request, flash

@app.route('/admin/news', methods=['GET', 'POST'])
def admin_news():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        if not title or not content:
            flash("Title and content are required.", "danger")
        else:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO news (title, content) VALUES (?, ?)", (title, content))
            conn.commit()
            conn.close()
            flash("News added successfully!", "success")
            return redirect(url_for('admin_news'))

    return render_template('admin_news.html')

@app.route('/news')
def news():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    role = session.get('role')
    if role == 'founder':
      home_url = url_for('founder_home')
    elif role == 'investor':
      home_url = url_for('investor_home')
    else:
      home_url = url_for('login')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM news ORDER BY created_at DESC")
    news_list = c.fetchall()
    conn.close()

    return render_template('news.html', news_list=news_list,user=session['username'], home_url=home_url)


# ----------------- Community Routes --------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/community', methods=['GET', 'POST'])
def community():
    if 'username' not in session:
        return redirect(url_for('login'))

    role = session.get('role')
    if role == 'founder':
        home_url = url_for('founder_home')
    elif role == 'investor':
        home_url = url_for('investor_home')
    else:
        home_url = url_for('login')

    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        content = request.form.get('content')
        file = request.files.get('image')
        image_path = None

        if file and allowed_file(file.filename):
          filename = secure_filename(file.filename)
          file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
          image_path = f'uploads/{filename}'  # relative to static folder

        if content or image_path:
            c.execute("INSERT INTO posts (username, role, content, image_path) VALUES (?, ?, ?, ?)",
                      (session['username'], role, content, image_path))
            conn.commit()

        conn.close()
        return redirect(url_for('community'))

    # Fetch posts
    c.execute("SELECT * FROM posts ORDER BY created_at DESC")
    posts = c.fetchall()

    comments_map = {}
    replies_map = {}

    for post in posts:
        c.execute("SELECT * FROM comments WHERE post_id=? ORDER BY created_at ASC", (post['id'],))
        comments = c.fetchall()
        comments_map[post['id']] = comments

        for comment in comments:
            c.execute("SELECT * FROM replies WHERE comment_id=? ORDER BY created_at ASC", (comment['id'],))
            replies_map[comment['id']] = c.fetchall()

    conn.close()
    return render_template('community.html', posts=posts, comments_map=comments_map,
                           replies_map=replies_map, user=session['username'], home_url=home_url)


@app.route('/community/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    content = request.form.get('comment')
    if content:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO comments (post_id, username, content) VALUES (?, ?, ?)",
                  (post_id, session['username'], content))
        conn.commit()
        conn.close()
    return redirect(url_for('community'))

@app.route('/community/reply/<int:comment_id>', methods=['POST'])
def add_reply(comment_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    content = request.form.get('reply')
    if content:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO replies (comment_id, username, content) VALUES (?, ?, ?)",
                  (comment_id, session['username'], content))
        conn.commit()
        conn.close()
    return redirect(url_for('community'))

@app.route('/community/delete_post/<int:post_id>')
def delete_post(post_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM posts WHERE id=? AND username=?", (post_id, session['username']))
    conn.commit()
    conn.close()
    return redirect(url_for('community'))

@app.route('/community/delete_comment/<int:comment_id>')
def delete_comment(comment_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM comments WHERE id=? AND username=?", (comment_id, session['username']))
    conn.commit()
    conn.close()
    return redirect(url_for('community'))

@app.route('/community/delete_reply/<int:reply_id>')
def delete_reply(reply_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM replies WHERE id=? AND username=?", (reply_id, session['username']))
    conn.commit()
    conn.close()
    return redirect(url_for('community'))

# ----------------- Profile Routes --------------------

# User profile route
@app.route('/profile/<username>')
def profile(username):
    if 'username' not in session:
        return redirect(url_for('login'))

    role = session.get('role')
    if role == 'founder':
        home_url = url_for('founder_home')
    elif role == 'investor':
        home_url = url_for('investor_home')
    else:
        home_url = url_for('login')

    conn = get_db_connection()
    c = conn.cursor()

    # Get user info
    c.execute("SELECT username, role FROM users WHERE username=?", (username,))
    user = c.fetchone()
    if not user:
        conn.close()
        return "User not found", 404

    profile_data = {'username': user['username'], 'role': user['role']}

    if user['role'] == 'founder':
        c.execute("SELECT * FROM projects WHERE founder_username=?", (username,))
        projects = c.fetchall()
        c.execute("SELECT * FROM team_members WHERE founder_username=?", (username,))
        team_members = c.fetchall()
        c.execute("SELECT * FROM goals WHERE founder_username=?", (username,))
        goals = c.fetchall()
        profile_data.update({
            'projects': projects,
            'team_members': team_members,
            'goals': goals
        })

    elif user['role'] == 'investor':
        c.execute("SELECT * FROM investors WHERE username=?", (username,))
        investor = c.fetchone()
        if investor:
            profile_data.update({
                'full_name': investor['full_name'],
                'email': investor['email'],
                'bio': investor['bio']
            })

    conn.close()
    return render_template('profile.html', profile=profile_data, user=session['username'], home_url=home_url)


# Search route
@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'username' not in session:
        return redirect(url_for('login'))

    query = ""
    results = []
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if query:
            conn = get_db_connection()
            c = conn.cursor()
            # Search users by username or name (case insensitive)
            c.execute("""
              SELECT username, role
              FROM users
              WHERE username LIKE ?
              LIMIT 50
              """, (f"%{query}%",))  # Note the comma here, makes it a tuple with one item

            results = c.fetchall()
            conn.close()

    return render_template('search.html', query=query, results=results)



# ----------------- Founder routes --------------------

@app.route('/founder/home')
def founder_home():
    if 'role' not in session or session['role'] != 'founder':
        return redirect(url_for('login'))

    founder_username = session['username']
    conn = get_db_connection()
    c = conn.cursor()

    # Fetch all projects
    c.execute("SELECT * FROM projects WHERE founder_username=?", (founder_username,))
    projects = c.fetchall()

    # Fetch all team members
    c.execute("SELECT * FROM team_members WHERE founder_username=?", (founder_username,))
    team_members = c.fetchall()

    # Fetch all goals
    c.execute("SELECT * FROM goals WHERE founder_username=?", (founder_username,))
    goals = c.fetchall()

    c.execute("SELECT COUNT(*) FROM goals WHERE founder_username=?", (founder_username,))
    total_goals = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM goals WHERE founder_username=? AND completed=1", (founder_username,))
    completed_goals = c.fetchone()[0]

    progress_percent = int((completed_goals / total_goals) * 100) if total_goals > 0 else 0


    # Calculate progress percentage
    total_goals = len(goals)
    completed_goals = sum(1 for g in goals if g['completed'] == 1)
    progress_percent = int((completed_goals / total_goals) * 100) if total_goals > 0 else 0

    # Celebration flag if all goals completed and total_goals > 0
    celebration = (completed_goals == total_goals and total_goals > 0)

    # Fetch news (optional display on founder page)
    c.execute("SELECT title, content, created_at FROM news ORDER BY created_at DESC")
    news_items = c.fetchall()

    conn.close()

    return render_template('founder_home.html', user=founder_username, projects=projects, team_members=team_members, goals=goals, celebration=(progress_percent == 100), progress_percent=progress_percent)


# Add New Project Route (GET form + POST handler)
@app.route('/founder/edit', methods=['GET', 'POST'], strict_slashes=False)
@app.route('/founder/edit/<int:project_id>', methods=['GET', 'POST'], strict_slashes=False)
def founder_edit(project_id=None):
    if 'role' not in session or session['role'] != 'founder':
        return redirect(url_for('login'))
    founder_username = session['username']

    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_project':
            project_name = request.form['project_name']
            project_desc = request.form['project_desc']
            c.execute("INSERT INTO projects (founder_username, project_name, project_desc) VALUES (?, ?, ?)",
                      (founder_username, project_name, project_desc))
            conn.commit()

        elif action == 'edit_project':
            project_id_form = int(request.form['project_id'])
            project_name = request.form['project_name']
            project_desc = request.form['project_desc']
            c.execute("UPDATE projects SET project_name=?, project_desc=? WHERE id=? AND founder_username=?",
                      (project_name, project_desc, project_id_form, founder_username))
            conn.commit()

        elif action == 'delete_project':
            project_id_form = int(request.form['project_id'])
            c.execute("DELETE FROM projects WHERE id=? AND founder_username=?", (project_id_form, founder_username))
            conn.commit()

        elif action == 'add_team_member':
            member_name = request.form['member_name']
            member_role = request.form['member_role']
            c.execute("INSERT INTO team_members (founder_username, member_name, member_role) VALUES (?, ?, ?)",
                      (founder_username, member_name, member_role))
            conn.commit()

        elif action == 'delete_team_member':
            member_id = int(request.form['member_id'])
            c.execute("DELETE FROM team_members WHERE id=? AND founder_username=?", (member_id, founder_username))
            conn.commit()

        elif action == 'add_goal':
            goal_desc = request.form['goal_desc']
            c.execute("INSERT INTO goals (founder_username, goal_desc, completed) VALUES (?, ?, 0)",
                      (founder_username, goal_desc))
            conn.commit()

        elif action == 'delete_goal':
            goal_id = int(request.form['goal_id'])
            c.execute("DELETE FROM goals WHERE id=? AND founder_username=?", (goal_id, founder_username))
            conn.commit()

        conn.close()
        return redirect(url_for('founder_edit'))

    # GET method — fetch all projects, members, goals
    c.execute("SELECT * FROM projects WHERE founder_username=?", (founder_username,))
    projects = c.fetchall()

    c.execute("SELECT * FROM team_members WHERE founder_username=?", (founder_username,))
    team_members = c.fetchall()

    c.execute("SELECT * FROM goals WHERE founder_username=?", (founder_username,))
    goals = c.fetchall()

    project = None
    if project_id is not None:
        c.execute("SELECT * FROM projects WHERE id=? AND founder_username=?", (project_id, founder_username))
        project = c.fetchone()

    conn.close()
    return render_template('founder_edit.html', user=founder_username, projects=projects,
                           project=project, team_members=team_members, goals=goals)



@app.route('/founder/goal/complete/<int:goal_id>', methods=['POST'])
def mark_goal_complete(goal_id):
    if 'role' not in session or session['role'] != 'founder':
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE goals SET completed = 1 WHERE id = ?", (goal_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('founder_home'))


# ----------------- Investor routes --------------------

@app.route('/investor/home')
def investor_home():
    if 'username' not in session or session.get('role') != 'investor':
        return redirect(url_for('login'))

    user = session['username']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM investors WHERE username=?", (user,))
    investor = c.fetchone()
    conn.close()

    if investor is None:
        # no investor found, handle gracefully
        investor = None

    return render_template('investor_home.html', user=user, investor=investor)

@app.route('/debug/investors')
def debug_investors():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM investors")
    rows = c.fetchall()
    conn.close()
    return "<br>".join([row['username'] for row in rows]) or "No investors found."


@app.route('/investor/edit', methods=['GET', 'POST'])
def investor_edit():
    if 'role' not in session or session['role'] != 'investor':
        return redirect(url_for('login'))

    user = session['username']
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        bio = request.form.get('bio', '')

        # Update investor info, password only if provided
        if password:
            c.execute('UPDATE investors SET full_name=?, email=?, password=?, bio=? WHERE username=?',
                      (full_name, email, password, bio, user))
        else:
            c.execute('UPDATE investors SET full_name=?, email=?, bio=? WHERE username=?',
                      (full_name, email, bio, user))

        conn.commit()
        conn.close()
        return redirect(url_for('investor_home'))

    # GET request - fetch current info
    c.execute('SELECT * FROM investors WHERE username=?', (user,))
    investor = c.fetchone()
    conn.close()

    return render_template('investor_edit.html', investor=investor)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
