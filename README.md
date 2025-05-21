# Flask Test

This repository contains a minimal Flask application with a small note taking
example using SQLite. The home page still displays "Hello, World!" and a new
"Notes" page lets you create notes with categories which are stored in a local
`notes.db` file.

## Setup

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Running

Run the application with:

```bash
python app.py
```

Then open [http://127.0.0.1:5000/](http://127.0.0.1:5000/) in your browser to see
the greeting. The notes page is available at
[http://127.0.0.1:5000/notes](http://127.0.0.1:5000/notes).
