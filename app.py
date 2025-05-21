from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from pathlib import Path

app = Flask(__name__)

DB_PATH = Path("notes.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/calc', methods=['GET', 'POST'])
def calc():
    result = None
    if request.method == 'POST':
        try:
            num1 = float(request.form['num1'])
            num2 = float(request.form['num2'])
            op = request.form['op']
            if op == '+':
                result = num1 + num2
            elif op == '-':
                result = num1 - num2
            elif op == '*':
                result = num1 * num2
            elif op == '/':
                result = 'Error: Division by zero' if num2 == 0 else num1 / num2
        except Exception:
            result = 'Error'
    return render_template('calc.html', result=result)


@app.route('/notes', methods=['GET', 'POST'])
def notes():
    conn = get_db_connection()
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        content = request.form['content']
        conn.execute(
            'INSERT INTO notes (title, category, content) VALUES (?, ?, ?)',
            (title, category, content),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('notes'))
    notes = conn.execute(
        'SELECT id, title, category, content FROM notes ORDER BY category, id DESC'
    ).fetchall()
    conn.close()
    return render_template('notes.html', notes=notes)

if __name__ == '__main__':
    init_db()
    app.run()

