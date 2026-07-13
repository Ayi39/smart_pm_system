"""
Smart Web-Based Task and Project Management System for SMEs
Backend: Python / Flask / MySQL
Author: Aisha Millicent Makaza (T2420082)
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
import bcrypt
from functools import wraps
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler
import mimetypes
import re
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')

app = Flask(__name__)
app.secret_key = "replace-this-with-a-long-random-secret-key"

# ---------------------------------------------------------
# Database connection settings
# Update these to match your local MySQL setup
# ---------------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "@Root123",          # set your MySQL root password here
    "database": "sme_task_management"
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


# ---------------------------------------------------------
# Authentication / RBAC helpers
# ---------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get("role") not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated
    return wrapper


# ---------------------------------------------------------
# Auth routes
# ---------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form.get("role", "team_member")

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO user (full_name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                (full_name, email, hashed.decode("utf-8"), role)
            )
            conn.commit()
            cur.close()
            conn.close()
            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("login"))
        except Error as e:
            flash(f"Registration failed: {e}", "danger")

    return render_template("register.html")


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM user WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            session["user_id"] = user["user_id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total FROM project")
    total_projects = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM task WHERE status != 'completed'")
    open_tasks = cur.fetchone()["total"]

    cur.execute("""
        SELECT task_id, title, deadline, status
        FROM task
        WHERE deadline >= CURDATE()
        ORDER BY deadline ASC LIMIT 5
    """)
    upcoming_deadlines = cur.fetchall()

    cur.execute("""
        SELECT u.full_name, COUNT(t.task_id) AS task_count
        FROM user u LEFT JOIN task t ON u.user_id = t.assigned_to
        WHERE u.role = 'team_member'
        GROUP BY u.user_id
    """)
    workload = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_projects=total_projects,
        open_tasks=open_tasks,
        upcoming_deadlines=upcoming_deadlines,
        workload=workload
    )


# ---------------------------------------------------------
# Project routes
# ---------------------------------------------------------
@app.route("/projects")
@login_required
@role_required("admin", "manager")
def projects():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM project ORDER BY created_at DESC")
    all_projects = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("projects.html", projects=all_projects)


@app.route("/projects/new", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def new_project():
    if request.method == "POST":
        name = request.form["project_name"]
        description = request.form["description"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO project (project_name, description, created_by) VALUES (%s, %s, %s)",
            (name, description, session["user_id"])
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Project created successfully.", "success")
        return redirect(url_for("projects"))

    return render_template("new_project.html")


@app.route("/projects/<int:project_id>")
@login_required
@role_required("admin", "manager")
def project_detail(project_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM project WHERE project_id = %s", (project_id,))
    project = cur.fetchone()

    cur.execute("""
        SELECT t.*, u.full_name AS assignee_name
        FROM task t LEFT JOIN user u ON t.assigned_to = u.user_id
        WHERE t.project_id = %s
        ORDER BY t.deadline ASC
    """, (project_id,))
    tasks = cur.fetchall()

    cur.execute("SELECT user_id, full_name FROM user WHERE role = 'team_member'")
    team_members = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("project_detail.html", project=project, tasks=tasks, team_members=team_members)


# ---------------------------------------------------------
# Task routes
# ---------------------------------------------------------
@app.route("/projects/<int:project_id>/tasks/new", methods=["POST"])
@login_required
@role_required("admin", "manager")
def new_task(project_id):
    title = request.form["title"]
    description = request.form["description"]
    assigned_to = request.form["assigned_to"]
    priority = request.form["priority"]
    deadline = request.form["deadline"]
    if not title.strip():
        flash("Task title cannot be empty.", "danger")
        return redirect(url_for("project_detail", project_id=project_id))
    if deadline < str(date.today()):
        flash("Deadline cannot be in the past.", "danger")
        return redirect(url_for("project_detail", project_id=project_id))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO task (project_id, assigned_to, title, description, priority, deadline)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (project_id, assigned_to, title, description, priority, deadline))
    conn.commit()
    cur.close()
    conn.close()
    flash("Task added successfully.", "success")
    return redirect(url_for("project_detail", project_id=project_id))




    if not task:
        cur.close(); conn.close()
        flash("Task not found.", "danger")
        return redirect(url_for("dashboard"))

    # Ownership check: team members may only update their own assigned tasks
    if session.get("role") == "team_member" and task["assigned_to"] != session["user_id"]:
        cur.close(); conn.close()
        flash("Only the team member assigned to this task can update its status.", "danger")
        if session.get("role") in ("admin", "manager"):
            return redirect(url_for("project_detail", project_id=task["project_id"]))
        return redirect(url_for("my_tasks"))

    cur.execute("UPDATE task SET status = %s WHERE task_id = %s", (new_status, task_id))
    conn.commit()
    project_id = task["project_id"]
    cur.close()
    conn.close()

@app.route("/tasks/<int:task_id>/status", methods=["POST"])
@login_required
def update_task_status(task_id):
    new_status = request.form["status"]

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT project_id, assigned_to FROM task WHERE task_id = %s", (task_id,))
    task = cur.fetchone()

    if not task:
        cur.close(); conn.close()
        flash("Task not found.", "danger")
        return redirect(url_for("dashboard"))

    if session.get("role") != "team_member" or task["assigned_to"] != session["user_id"]:
        cur.close(); conn.close()
        flash("Only the team member assigned to this task can update its status.", "danger")
        if session.get("role") in ("admin", "manager"):
            return redirect(url_for("project_detail", project_id=task["project_id"]))
        return redirect(url_for("my_tasks"))

    cur.execute("UPDATE task SET status = %s WHERE task_id = %s", (new_status, task_id))
    conn.commit()
    cur.close()
    conn.close()

    flash("Task status updated.", "success")
    return redirect(url_for("my_tasks"))

@app.route("/my-tasks")
@login_required
def my_tasks():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT t.*, p.project_name
        FROM task t JOIN project p ON t.project_id = p.project_id
        WHERE t.assigned_to = %s
        ORDER BY t.deadline ASC
    """, (session["user_id"],))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("my_tasks.html", tasks=tasks)

# ---------------------------------------------------------
# ---------------------------------------------------------
# Task detail + comments (Section 4.3 Sprint 3 - commenting capability)
# ---------------------------------------------------------
@app.route("/tasks/<int:task_id>")
@login_required
def task_detail(task_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT t.*, p.project_name, u.full_name AS assignee_name
        FROM task t
        JOIN project p ON t.project_id = p.project_id
        LEFT JOIN user u ON t.assigned_to = u.user_id
        WHERE t.task_id = %s
    """, (task_id,))
    task = cur.fetchone()

    if not task:
        cur.close(); conn.close()
        flash("Task not found.", "danger")
        return redirect(url_for("dashboard"))

    if session.get("role") == "team_member" and task["assigned_to"] != session["user_id"]:
        cur.close(); conn.close()
        flash("You do not have permission to view that task.", "danger")
        return redirect(url_for("my_tasks"))

    cur.execute("""
        SELECT c.comment_text, c.created_at, u.full_name
        FROM comment c JOIN user u ON c.user_id = u.user_id
        WHERE c.task_id = %s ORDER BY c.created_at ASC
    """, (task_id,))
    comments = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("task_detail.html", task=task, comments=comments)


@app.route("/tasks/<int:task_id>/comments", methods=["POST"])
@login_required
def add_comment(task_id):
    comment_text = request.form["comment_text"].strip()
    if comment_text:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO comment (task_id, user_id, comment_text) VALUES (%s, %s, %s)",
            (task_id, session["user_id"], comment_text)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Comment added.", "success")
    return redirect(url_for("task_detail", task_id=task_id))
# User management (admin only) - Section 4.2 RBAC
# ---------------------------------------------------------
@app.route("/users")
@login_required
@role_required("admin")
def manage_users():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id, full_name, email, role, created_at FROM user ORDER BY created_at DESC")
    all_users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("users.html", users=all_users)


@app.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
@role_required("admin")
def update_user_role(user_id):
    new_role = request.form["role"]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE user SET role = %s WHERE user_id = %s", (new_role, user_id))
    conn.commit()
    cur.close()
    conn.close()
    flash("User role updated successfully.", "success")
    return redirect(url_for("manage_users"))


# ---------------------------------------------------------
# Reporting
# ---------------------------------------------------------
@app.route("/reports")
@login_required
@role_required("admin", "manager")
def reports():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT p.project_name,
               COUNT(t.task_id) AS total_tasks,
               SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) AS completed_tasks
        FROM project p LEFT JOIN task t ON p.project_id = t.project_id
        GROUP BY p.project_id
    """)
    report_data = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("reports.html", report_data=report_data)


# ---------------------------------------------------------
# Automated deadline notification job (Section 4.4 / 4.7)
# Prevents duplicate notifications by checking the Notification table first
# ---------------------------------------------------------
def check_deadlines_and_notify():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT task_id, assigned_to, title, deadline
        FROM task
        WHERE status != 'completed'
        AND deadline BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 2 DAY)
    """)
    due_soon = cur.fetchall()

    for task in due_soon:
        if not task["assigned_to"]:
            continue

        cur.execute("""
            SELECT * FROM notification
            WHERE task_id = %s AND user_id = %s AND DATE(sent_at) = CURDATE()
        """, (task["task_id"], task["assigned_to"]))
        already_sent = cur.fetchone()

        if not already_sent:
            message = f"Reminder: Task '{task['title']}' is due on {task['deadline']}."
            cur.execute(
                "INSERT INTO notification (user_id, task_id, message) VALUES (%s, %s, %s)",
                (task["assigned_to"], task["task_id"], message)
            )
            conn.commit()
            print(f"[Notification] {message} -> user_id {task['assigned_to']}")

    cur.close()
    conn.close()


scheduler = BackgroundScheduler()
scheduler.add_job(check_deadlines_and_notify, "interval", hours=24, next_run_time=datetime.now())
scheduler.start()


@app.route("/notifications")
@login_required
def notifications():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT * FROM notification WHERE user_id = %s ORDER BY sent_at DESC
    """, (session["user_id"],))
    notes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("notifications.html", notifications=notes)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
