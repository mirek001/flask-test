from flask import Flask, render_template, request, redirect, url_for, jsonify
import calendar
import datetime
import sqlite3
from pathlib import Path
import requests

app = Flask(__name__)

DB_PATH = Path("notes.db")
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
# Use the local Mistral model for note generation
OLLAMA_MODEL = "mistral"


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
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            quantity TEXT NOT NULL,
            supplier TEXT NOT NULL,
            delivery_date TEXT NOT NULL
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


@app.route('/generate_note', methods=['POST'])
def generate_note():
    data = request.get_json()
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    try:
        resp = requests.post(
            OLLAMA_API_URL,
            json={'model': OLLAMA_MODEL, 'prompt': prompt, 'stream': False},
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json().get('response', '')
        return jsonify({'note': text})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/deliveries', methods=['GET', 'POST'])
def deliveries():
    conn = get_db_connection()
    if request.method == 'POST':
        item = request.form['item']
        quantity = request.form['quantity']
        supplier = request.form['supplier']
        delivery_date = request.form['delivery_date']
        conn.execute(
            'INSERT INTO deliveries (item, quantity, supplier, delivery_date) VALUES (?, ?, ?, ?)',
            (item, quantity, supplier, delivery_date),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('deliveries'))
    deliveries = conn.execute(
        'SELECT id, item, quantity, supplier, delivery_date FROM deliveries ORDER BY id DESC'
    ).fetchall()
    conn.close()
    return render_template('deliveries.html', deliveries=deliveries)


@app.route('/delete_delivery/<int:delivery_id>', methods=['POST'])
def delete_delivery(delivery_id):
    """Delete a delivery entry."""
    conn = get_db_connection()
    conn.execute('DELETE FROM deliveries WHERE id = ?', (delivery_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('deliveries'))


@app.route('/calendar')
def calendar_view():
    today = datetime.date.today()
    year = today.year
    month = today.month
    conn = get_db_connection()
    deliveries = conn.execute(
        "SELECT id, item, quantity, supplier, delivery_date FROM deliveries WHERE strftime('%Y-%m', delivery_date) = ?",
        (f"{year:04d}-{month:02d}",),
    ).fetchall()
    conn.close()
    deliveries_by_day = {}
    for d in deliveries:
        day = int(d['delivery_date'].split('-')[2])
        deliveries_by_day.setdefault(day, []).append(d)
    weeks = calendar.monthcalendar(year, month)
    return render_template(
        'calendar.html',
        weeks=weeks,
        deliveries_by_day=deliveries_by_day,
        year=year,
        month=month,
    )


@app.route('/move_delivery', methods=['POST'])
def move_delivery():
    data = request.get_json()
    delivery_id = int(data.get('id'))
    new_date = data.get('new_date')
    conn = get_db_connection()
    conn.execute(
        'UPDATE deliveries SET delivery_date = ? WHERE id = ?',
        (new_date, delivery_id),
    )
    conn.commit()
    conn.close()
    return '', 204

if __name__ == '__main__':
    init_db()
    app.run()

