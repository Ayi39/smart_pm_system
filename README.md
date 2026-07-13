# Smart Web-Based Task and Project Management System — Setup Guide

## 1. Install prerequisites (one-time)
- Install **Python 3.10+**: python.org
- Install **XAMPP** (gives you MySQL + phpMyAdmin easily): apachefriends.org
  - Start "MySQL" from the XAMPP control panel

## 2. Set up the database
1. Open phpMyAdmin (http://localhost/phpmyadmin) or use the MySQL command line.
2. Import `schema.sql` (phpMyAdmin: Import tab → choose file → Go).
   This creates the `smart_pm_system` database with the User, Project,
   Task, Comment, and Notification tables.

## 3. Set up the Python environment
Open a terminal/command prompt in the project folder:

```
python -m venv venv
venv\Scripts\activate        (Windows)
source venv/bin/activate     (Mac/Linux)

pip install -r requirements.txt
```

If your MySQL root user has a password, open `app.py` and update
`DB_CONFIG["password"]` accordingly.

## 4. Run the application
```
python app.py
```
Open your browser at **http://127.0.0.1:5000**

## 5. Taking screenshots for Chapter 4

Register 3 accounts first (one of each role) at `/register`:
- An **admin**
- A **manager**
- A **team member**

Then log in as each and capture these screens — they map directly to
Chapter 4 sections:

| Screenshot | Where to find it | Chapter 4 section |
|---|---|---|
| Registration form | `/register` | 4.2 Front End Design |
| Login form | `/login` | 4.2 Front End Design |
| Dashboard with stats/deadlines | `/dashboard` (as manager) | 4.2 Front End Design |
| Projects list | `/projects` | 4.3 Prototype Construction |
| New project form | `/projects/new` | 4.3 Prototype Construction |
| Project detail with task table | `/projects/<id>` | 4.4 Integration of Components |
| Add task form | bottom of project detail page | 4.3 Prototype Construction |
| Task status dropdown in action | project detail page | 4.4 Integration of Components |
| My Tasks (as team member) | `/my-tasks` | 4.2 Back End Design (RBAC) |
| Reports page | `/reports` (as manager/admin) | 4.5 Programming |
| Notifications page | `/notifications` | 4.4 Integration (APScheduler) |
| MySQL tables in phpMyAdmin | phpMyAdmin → smart_pm_system | 4.2 Database Design |
| app.py code open in an editor | VS Code | 4.5 Programming |
| schema.sql code open in an editor | VS Code | 4.2 Database Design |

Tip: Use Windows Snipping Tool (Win+Shift+S) or Mac Screenshot
(Cmd+Shift+4) so each image is cropped to just the browser window —
your supervisor wants clear, labelled screenshots, not full-desktop
captures.

## 6. Optional: push to GitHub for the "Git version control" evidence
```
git init
git add .
git commit -m "Initial commit - Smart PM System prototype"
```
Then create a repository on GitHub and push it — a screenshot of the
commit history/branches supports Section 4.5 (Programming) where the
report mentions Git and GitHub.
