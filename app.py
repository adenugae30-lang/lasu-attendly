import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = os.urandom(24)
DATABASE = 'lasu_attendly.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                fullname TEXT NOT NULL,
                matric TEXT NOT NULL,
                course TEXT NOT NULL,
                status TEXT DEFAULT 'Present',
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

init_db()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('username').strip()
        password = request.form.get('password')
        
        with get_db() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE username = ? OR email = ?', 
                (identifier, identifier)
            ).fetchone()
            
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['fullname'] = user['fullname']
            flash('Signed in successfully!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials. Please check your username and password.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form.get('fullname').strip()
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')
        
        hashed_pw = generate_password_hash(password)
        try:
            with get_db() as conn:
                conn.execute(
                    'INSERT INTO users (fullname, username, email, password) VALUES (?, ?, ?, ?)',
                    (fullname, username, email, hashed_pw)
                )
                conn.commit()
            flash('Account created successfully! Please sign in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or Email already exists.', 'error')
    return render_template('signup.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        identifier = request.form.get('identifier').strip()
        flash(f'Password reset instructions sent (if account exists for: {identifier})', 'info')
        return redirect(url_for('login'))
    return render_template('forgot-password.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        fullname = request.form.get('fullname').strip()
        matric = request.form.get('matric').strip().upper()
        course = request.form.get('course').strip().upper()
        
        with get_db() as conn:
            conn.execute(
                'INSERT INTO students (user_id, fullname, matric, course, status) VALUES (?, ?, ?, ?, ?)',
                (user_id, fullname, matric, course, 'Present')
            )
            conn.commit()
        return redirect(url_for('dashboard'))
        
    with get_db() as conn:
        students = conn.execute('SELECT * FROM students WHERE user_id = ?', (user_id,)).fetchall()
        
    total = len(students)
    present = sum(1 for s in students if s['status'] == 'Present')
    absent = total - present
    
    return render_template('dashboard.html', students=students, total=total, present=present, absent=absent, username=session['username'])

@app.route('/update-status/<int:student_id>/<status>')
def update_status(student_id, status):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if status in ['Present', 'Absent']:
        with get_db() as conn:
            conn.execute('UPDATE students SET status = ? WHERE id = ? AND user_id = ?', (status, student_id, session['user_id']))
            conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete-student/<int:student_id>')
def delete_student(student_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with get_db() as conn:
        conn.execute('DELETE FROM students WHERE id = ? AND user_id = ?', (student_id, session['user_id']))
        conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'profile':
            fullname = request.form.get('fullname').strip()
            username = request.form.get('username').strip()
            email = request.form.get('email').strip()
            try:
                with get_db() as conn:
                    conn.execute('UPDATE users SET fullname = ?, username = ?, email = ? WHERE id = ?', (fullname, username, email, user_id))
                    conn.commit()
                session['username'] = username
                session['fullname'] = fullname
                flash('Profile updated successfully!', 'success')
            except sqlite3.IntegrityError:
                flash('Username or Email already taken.', 'error')
        elif action == 'password':
            current_pw = request.form.get('current_password')
            new_pw = request.form.get('new_password')
            if check_password_hash(user['password'], current_pw):
                hashed_new = generate_password_hash(new_pw)
                with get_db() as conn:
                    conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_new, user_id))
                    conn.commit()
                flash('Password updated successfully!', 'success')
            else:
                flash('Incorrect current password.', 'error')
        return redirect(url_for('settings'))
        
    return render_template('settings.html', user=user)

@app.route('/download-pdf')
def download_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    with get_db() as conn:
        students = conn.execute('SELECT * FROM students WHERE user_id = ?', (user_id,)).fetchall()
        
    response = make_response()
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=lasu_attendance_report.pdf'
    
    doc = SimpleDocTemplate(response.raw, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#008751'), spaceAfter=4, alignment=1)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#555555'), spaceAfter=20, alignment=1)
    
    story.append(Paragraph('<b>LASU Attendly</b>', title_style))
    story.append(Paragraph('Official Course Attendance & Results Report — Lagos State University', subtitle_style))
    story.append(Spacer(1, 10))
    
    total = len(students)
    present = sum(1 for s in students if s['status'] == 'Present')
    absent = total - present
    
    summary_text = f"<b>Total Enrolled:</b> {total} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Present:</b> {present} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Absent:</b> {absent}"
    story.append(Paragraph(summary_text, styles['Normal']))
    story.append(Spacer(1, 15))
    
    table_data = [['S/N', 'Full Name', 'Matric Number', 'Course Code', 'Status']]
    for i, s in enumerate(students, 1):
        table_data.append([str(i), s['fullname'], s['matric'], s['course'], s['status']])
        
    t = Table(table_data, colWidths=[40, 180, 120, 100, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#008751')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
    ]))
    story.append(t)
    
    doc.build(story)
    return response

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)