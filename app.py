from flask import Flask, flash, render_template, request, redirect, session, url_for, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta

from helpers import get_db, login_required, create_tables, get_from_users, insert_user, goal_required, age_multiplier, activity_multiplier, set_goals, check_progress

app = Flask(__name__) # <- initializes the Flask application
app.secret_key = "secretkey"

# Configure session
app.config["SESSION_PERMANENT"] = False  # session expires when browser closes
app.config["SESSION_TYPE"] = "filesystem"  # store session data in files
Session(app)

# create tables for db if not exist
create_tables()


@app.route('/')
@login_required
@goal_required
def index():
    print(session["goal"])
    check_progress()
    print(session["current"])
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

         # Check both fields
        if not username or not password:
            if not username:
                flash("Username cannot be empty", "username_error")
            if not password:
                flash("Password cannot be empty", "password_error")
            return redirect(url_for("login"))
        
        # Check with database
        user = get_from_users(username, password)
        if not user:
            flash("Invalid username or password", "login_error")
            return redirect(url_for("login"))
        
        # Login successful
        session["user_id"] = user["id"]  # store user ID in session
        session["username"] = user["username"]
        session["goal"] = user["daily_goal"]
        flash("Logged in successfully!", "success")
        return redirect(url_for("index")) 

    # GET request: render the login page
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # check empty username or password
        if not username or not password or not confirmation:
            if not username:
                flash("Username cannot be empty", "username_error")
            if not password:
                flash("Password cannot be empty", "password_error")
            if not confirmation:
                flash("Confirmation cannot be empty", "confirmation_error")
            return redirect(url_for("register"))
        
        # check if password match confirmation and if username doesn't already exist
        if password != confirmation:
            flash("Password doesn't match confirmation", "match_error")
            return redirect(url_for("register"))

        if not insert_user(username, password):
            flash("Username taken", "username_error")
            return redirect(url_for("register"))

        # If we reach here, user is successfully inserted
        user = get_from_users(username, password)
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["goal"] = user["daily_goal"]  
        return redirect(url_for("index")) # log user in 
        

    return render_template('register.html')

@app.route("/logout")
def logout():
    
    # empty session
    session.clear()
    return redirect(url_for("index"))

# set initial daily target of water intake or allow user to reset goals
@app.route("/goal", methods=["GET", "POST"])
@login_required
def goal():
    if request.method == "POST":
        try:
            weight = float(request.form.get("weight"))
            activity = int(request.form.get("activity"))
            age = int(request.form.get("age"))
        except ValueError:
            flash("Please input valid values for weight, activity, and age group", "value_error")
            return redirect(url_for("goal"))
        
        # check values of activity and age
        if activity < 1 or activity > 5 or age < 1 or age > 4:
            if activity < 1 or activity > 5:
                flash("Invalid value for activity, please try again", "value_error")
                return redirect(url_for("goal"))

            if age < 1 or age > 4:
                flash("Invalid value for age, please try again", "value_error")
                return redirect(url_for("goal"))

        base_per_kg = 35 # ml per kg
        goal = weight * base_per_kg * activity_multiplier[str(activity)] * age_multiplier[str(age)]
        set_goals(goal)

        flash("Successfully set goal!", "success")
        return redirect(url_for("index"))
        
    return render_template("goal.html")

@app.route("/add_water", methods=["POST"])
@login_required
def add_water():
    data = request.get_json()
    amount = data.get("amount")

    # connect to db
    conn = get_db()
    c = conn.cursor()

    # update database of current_value
    c.execute("""
        UPDATE progress
        SET current = current + ?
        WHERE user_id = ?
        AND date = DATE('now')
    """, (amount, session["user_id"]))
    conn.commit()

    # select updated current value
    c. execute("""
        SELECT current 
        FROM progress
        WHERE user_id = ?
        AND date = DATE('now')
    """, (session["user_id"],))
    row = c.fetchone()

    conn.close()

    # return updated current value as JSON

    updated_current = row["current"] if row else 0 
    return jsonify({"updated_current": updated_current})

@app.route("/reset_water", methods=["POST"])
@login_required
def reset_water():

    # connect to database
    conn = get_db()
    c = conn.cursor()

    # reset current from progress database
    c.execute("""
        UPDATE progress
        SET current = 0
        WHERE user_id = ?
        AND date = DATE('now')
    """, (session["user_id"],))

    conn.commit()
    conn.close()

    # return current = 0 as JSON to js
    return jsonify({"reset_current": 0})

# history of user's drinking habits
@app.route("/history")
@login_required
def history():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    today = datetime.now().date()
    one_month_ago = today - timedelta(days=30)
    
    # Create list of dates for the past 31 days
    dates_list = [one_month_ago + timedelta(days=i) for i in range(31)]
    
    # Group dates by month
    from collections import defaultdict
    dates_by_month = defaultdict(list)
    
    for date in dates_list:
        month_key = date.strftime('%B %Y')  # e.g., "September 2025"
        dates_by_month[month_key].append(date)
    
    # Fetch water intake data
    c.execute("""
        SELECT date, current 
        FROM progress 
        WHERE user_id = :user_id 
        AND date >= :start_date 
        AND date <= :end_date
        ORDER BY date
    """, {
        "user_id": session["user_id"],
        "start_date": str(one_month_ago),
        "end_date": str(today)
    })
    
    intake_data = c.fetchall()
    conn.close()
    
    intake_dict = {row['date']: row['current'] for row in intake_data}
    goal = session.get('goal', 2000)
    
    return render_template("history.html", 
                         intake_dict=intake_dict,
                         dates_by_month=dates_by_month,
                         goal=goal)

# include for debugging, run with python app.py
if __name__ == "__main__":
    app.run(debug=True)