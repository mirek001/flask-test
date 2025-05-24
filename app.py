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

# Simple configuration for unloading gates and storage zones
GATES = ["Gate 1", "Gate 2", "Gate 3"]
ZONES = ["Zone A", "Zone B", "Zone C"]


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
            delivery_date TEXT NOT NULL,
            delivery_time TEXT DEFAULT '',
            gate TEXT DEFAULT '',
            zone TEXT DEFAULT ''
        )
        """
    )
    # Ensure new columns exist if database was created with an older schema
    current = [row[1] for row in c.execute("PRAGMA table_info(deliveries)")]
    for col in ["delivery_time", "gate", "zone"]:
        if col not in current:
            c.execute(f"ALTER TABLE deliveries ADD COLUMN {col} TEXT DEFAULT ''")

    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def send_notification(message: str) -> None:
    """Write notification messages to a log file and stdout."""
    log_path = Path("notifications.log")
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(message + "\n")
    print(message)

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
        delivery_time = request.form['delivery_time']
        gate = request.form['gate']
        zone = request.form['zone']
        conn.execute(
            'INSERT INTO deliveries (item, quantity, supplier, delivery_date, delivery_time, gate, zone) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (item, quantity, supplier, delivery_date, delivery_time, gate, zone),
        )
        conn.commit()
        send_notification(
            f"Delivery scheduled: {item} x{quantity} from {supplier} on {delivery_date} {delivery_time} at {gate} / {zone}"
        )
        conn.close()
        return redirect(url_for('deliveries'))
    deliveries = conn.execute(
        'SELECT id, item, quantity, supplier, delivery_date, delivery_time, gate, zone FROM deliveries ORDER BY id DESC'
    ).fetchall()
    conn.close()
    return render_template('deliveries.html', deliveries=deliveries, gates=GATES, zones=ZONES)


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
    """Display deliveries for a selected period."""
    period = request.args.get("period", "month")
    today = datetime.date.today()
    year_param = request.args.get("year")
    month_param = request.args.get("month")

    conn = get_db_connection()

    if period == "today":
        deliveries = conn.execute(
            "SELECT id, item, quantity, supplier, delivery_date, delivery_time, gate, zone FROM deliveries WHERE delivery_date = ?",
            (today.isoformat(),),
        ).fetchall()
        conn.close()
        return render_template(
            "calendar.html", period=period, today=today, deliveries=deliveries
        )

    if period == "tomorrow":
        tomorrow = today + datetime.timedelta(days=1)
        deliveries = conn.execute(
            "SELECT id, item, quantity, supplier, delivery_date, delivery_time, gate, zone FROM deliveries WHERE delivery_date = ?",
            (tomorrow.isoformat(),),
        ).fetchall()
        conn.close()
        return render_template(
            "calendar.html", period=period, tomorrow=tomorrow, deliveries=deliveries
        )

    if period == "week":
        start = today - datetime.timedelta(days=today.weekday())
        end = start + datetime.timedelta(days=6)
        deliveries = conn.execute(
            "SELECT id, item, quantity, supplier, delivery_date, delivery_time, gate, zone FROM deliveries WHERE delivery_date BETWEEN ? AND ?",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        conn.close()
        deliveries_by_day = {}
        for d in deliveries:
            deliveries_by_day.setdefault(d["delivery_date"], []).append(d)
        days = [start + datetime.timedelta(days=i) for i in range(7)]
        return render_template(
            "calendar.html",
            period=period,
            days=days,
            deliveries_by_day=deliveries_by_day,
        )

    if period == "year":
        year = today.year
        deliveries = conn.execute(
            "SELECT delivery_date FROM deliveries WHERE strftime('%Y', delivery_date) = ?",
            (f"{year:04d}",),
        ).fetchall()
        conn.close()
        deliveries_by_month = {}
        for d in deliveries:
            m = int(d["delivery_date"][5:7])
            deliveries_by_month[m] = deliveries_by_month.get(m, 0) + 1
        months = range(1, 13)
        return render_template(
            "calendar.html",
            period=period,
            year=year,
            months=months,
            deliveries_by_month=deliveries_by_month,
        )

    # Default is month view
    if year_param and month_param:
        try:
            year = int(year_param)
            month = int(month_param)
        except ValueError:
            year = today.year
            month = today.month
    else:
        year = today.year
        month = today.month
    deliveries = conn.execute(
        "SELECT id, item, quantity, supplier, delivery_date, delivery_time, gate, zone FROM deliveries WHERE strftime('%Y-%m', delivery_date) = ?",
        (f"{year:04d}-{month:02d}",),
    ).fetchall()
    conn.close()
    deliveries_by_day = {}
    for d in deliveries:
        day = int(d["delivery_date"].split("-")[2])
        deliveries_by_day.setdefault(day, []).append(d)
    weeks = calendar.monthcalendar(year, month)
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1
    return render_template(
        "calendar.html",
        period="month",
        weeks=weeks,
        deliveries_by_day=deliveries_by_day,
        year=year,
        month=month,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
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
    send_notification(f"Delivery {delivery_id} moved to {new_date}")
    return '', 204

if __name__ == '__main__':
    init_db()
    app.run()

