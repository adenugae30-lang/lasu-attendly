import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'lasu_attendly.db'

def get_db():
    """Establishes a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates necessary tables if they don't exist."""
    with get_db() as conn:
        # Users table for authentication and profile management
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # Students table linked to individual users (lecturers/admins)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                fullname TEXT NOT NULL,
                matric TEXT NOT NULL,
                course TEXT NOT NULL,
                status TEXT DEFAULT 'Present',
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()


class User:
    @staticmethod
    def create(fullname, username, email, password):
        """Creates a new user with a securely hashed password."""
        hashed_pw = generate_password_hash(password)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (fullname, username, email, password) VALUES (?, ?, ?, ?)',
                (fullname, username, email, hashed_pw)
            )
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def find_by_identifier(identifier):
        """Finds a user by username or email address."""
        with get_db() as conn:
            return conn.execute(
                'SELECT * FROM users WHERE username = ? OR email = ?',
                (identifier, identifier)
            ).fetchone()

    @staticmethod
    def find_by_id(user_id):
        """Finds a user by their unique primary key ID."""
        with get_db() as conn:
            return conn.execute(
                'SELECT * FROM users WHERE id = ?',
                (user_id,)
            ).fetchone()

    @staticmethod
    def update_profile(user_id, fullname, username, email):
        """Updates user profile information."""
        with get_db() as conn:
            conn.execute(
                'UPDATE users SET fullname = ?, username = ?, email = ? WHERE id = ?',
                (fullname, username, email, user_id)
            )
            conn.commit()

    @staticmethod
    def update_password(user_id, new_password):
        """Updates user password with a fresh secure hash."""
        hashed_pw = generate_password_hash(new_password)
        with get_db() as conn:
            conn.execute(
                'UPDATE users SET password = ? WHERE id = ?',
                (hashed_pw, user_id)
            )
            conn.commit()

    @staticmethod
    def verify_password(stored_password, provided_password):
        """Verifies a plain text password against a hashed password."""
        return check_password_hash(stored_password, provided_password)


class Student:
    @staticmethod
    def add(user_id, fullname, matric, course, status='Present'):
        """Adds a new student attendance record for a specific user."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO students (user_id, fullname, matric, course, status) VALUES (?, ?, ?, ?, ?)',
                (user_id, fullname, matric, course, status)
            )
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def get_by_user(user_id):
        """Retrieves all students registered by a specific user."""
        with get_db() as conn:
            return conn.execute(
                'SELECT * FROM students WHERE user_id = ?',
                (user_id,)
            ).fetchall()

    @staticmethod
    def update_status(student_id, user_id, status):
        """Updates attendance status (Present / Absent) for a student."""
        with get_db() as conn:
            conn.execute(
                'UPDATE students SET status = ? WHERE id = ? AND user_id = ?',
                (status, student_id, user_id)
            )
            conn.commit()

    @staticmethod
    def delete(student_id, user_id):
        """Deletes a student record."""
        with get_db() as conn:
            conn.execute(
                'DELETE FROM students WHERE id = ? AND user_id = ?',
                (student_id, user_id)
            )
            conn.commit()