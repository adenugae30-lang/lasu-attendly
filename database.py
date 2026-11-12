import sqlite3
from flask import g

DATABASE = 'lasu_attendly.db'

def get_db():
    """Opens a new database connection if there is none for the current application context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # Enables column access by name (e.g., row['username'])
    return g.db

def close_db(e=None):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    """Registers database teardown and initializes tables."""
    app.teardown_appcontext(close_db)
    
    with app.app_context():
        db = get_db()
        
        # 1. Users Table (Lecturers / Admins)
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # 2. Students Attendance Table linked to Users
        db.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                fullname TEXT NOT NULL,
                matric TEXT NOT NULL,
                course TEXT NOT NULL,
                status TEXT DEFAULT 'Present',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        db.commit()