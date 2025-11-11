import sqlite3
from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# the decorator is really just wrapping extra behavior around the original function call.

def get_db():
    conn = sqlite3.connect('users.db') # Connect to your database
    conn.row_factory = sqlite3.Row # To return rows as dictionaries
    return conn

def create_tables():
    """Create tables if it doesn't exist"""
    conn = get_db()
    c = conn.cursor()
    
    # Create table if it doesn't exist
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            hash TEXT NOT NULL,
            daily_goal REAL
        );

        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            current REAL DEFAULT 0,
            actual REAL DEFAULT 0,
            date DATE DEFAULT (DATE('now')),
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE (user_id, date)
        );
    """)


    # create a new table, for current_amount, actual_amount, DATE, id, user_id (FOREIGN)
    # actual_amount will be current_amount, until end of day
    # if end of day, update actual amount, insert new row for new day
    
    # For existing tables, add the column if missing
    try:
        c.execute("ALTER TABLE users ADD COLUMN daily_goal REAL")
        conn.commit()
        print("Added daily_goal column to existing table")
    except:
        pass  # Column already exists, no problem
    
    conn.close()

def insert_user(username, password): # <- for registration
    conn = get_db()
    c = conn.cursor()
    hash = generate_password_hash(password)
    try:
        c.execute("INSERT INTO users (username, hash) VALUES (:user_name, :hashed)", 
                {"user_name": username, "hashed": hash} 
                )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close() 
        return False
    
    conn.close()
    return True

def get_from_users(username, password): # <- for login
    conn = get_db()
    c = conn.cursor() # <- a cursor is like a shopping cart, stores data you chose

    # query database for user
    c.execute(
        "SELECT * FROM users WHERE username = :user_name",
        {"user_name": username}
    )
    user = c.fetchone()
    conn.close()

    # return one row if exist, none if does not exist
    if not user:
        return None
    
    # check password match hash
    if not check_password_hash(user["hash"], password):
        return None 
    return user


def login_required(f):
    @wraps(f) # preserves the original function's metadata, helps with identification and debugging
    def decorated_function(*args, **kwargs): # accepts any number of positional and keyword arguments
        if 'user_id' not in session:
            flash('You need to be logged in to access this page.', 'warning')
            return redirect(url_for('login')) # make sure function name matches 'login'   
        return f(*args, **kwargs)
    return decorated_function

# require user to already set intake goals
def goal_required(f):
    @wraps(f) # preserves the original functions's metadata, helps with identification and debugging
    def wrapper(*args, **kwargs):
        if "goal" not in session or session["goal"] is None:
            return redirect(url_for('goal'))
        return f(*args, **kwargs)
    return wrapper

# create dict to store age and activity multipliers
activity_multiplier = {
    "1":1.0,
    "2":1.17,
    "3":1.33,
    "4":1.5,
    "5":1.67
    }

age_multiplier = {
    "1":1.05,
    "2":1.0,
    "3":0.95,
    "4":0.9
}

def set_goals(goal):
    conn = get_db() 
    c = conn.cursor()

    # Always UPDATE since user already exists in the table
    c.execute(
        "UPDATE users SET daily_goal = :goal WHERE username = :user_name",
        {"goal": goal, "user_name": session["username"]}
    )
    
    # Update session with new goal
    session["goal"] = goal
    
    conn.commit()
    conn.close()

def check_progress():
    conn = get_db()
    c = conn.cursor()
    user_id = session["user_id"]
    today = datetime.now().date()
    recent_date = today - relativedelta(months=1)

    # 1️⃣ Fetch earliest progress date
    c.execute("""
        SELECT MIN(date) AS first_date FROM progress
        WHERE user_id = ?
    """, (user_id,))
    row = c.fetchone()
    first_date_str = row["first_date"] if row else None

    # 2️⃣ If no progress record exists yet (new user)
    if not first_date_str:
        c.execute("INSERT INTO progress (user_id, date) VALUES (?, DATE('now'))", (user_id,))
        conn.commit()
        first_date = today
    else:
        first_date = datetime.strptime(first_date_str, "%Y-%m-%d").date()

    # 3️⃣ Delete records older than one month ago
    c.execute("""
        DELETE FROM progress
        WHERE user_id = ? AND date < ?
    """, (user_id, recent_date.isoformat()))
    conn.commit()

    # 4️⃣ Fill in missing days (within the past month)
    days_in_month = (today - recent_date).days
    for i in range(0, days_in_month + 1):
        missing_date = recent_date + timedelta(days=i)
        c.execute("""
            INSERT OR IGNORE INTO progress (user_id, date, current, actual)
            VALUES (?, ?, 0, 0)
        """, (user_id, missing_date.isoformat()))
    conn.commit()

    # 5️⃣ Double-check that today's record exists
    try:
        c.execute("INSERT INTO progress (user_id, date) VALUES (?, DATE('now'))", (user_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # record already exists

    # 6️⃣ Load today's progress into session
    c.execute("""
        SELECT current FROM progress
        WHERE user_id = ? AND date = DATE('now')
    """, (user_id,))
    row = c.fetchone()
    if row:
        session["current"] = row["current"]

    conn.close()
