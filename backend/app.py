from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

DB_NAME = "database.db"

# ---------- DATABASE CONNECTION ----------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- CREATE TABLES ----------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    # Activities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_name TEXT,
            category TEXT,
            duration REAL,
            date TEXT,
            mood TEXT,
            goal TEXT,
            notes TEXT,
            prediction TEXT
        )
    """)

    conn.commit()
    conn.close()

# ---------- API TO ADD ACTIVITY ----------
@app.route("/add-activity", methods=["POST"])
def add_activity():
    data = request.json

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO activities 
        (activity_name, category, duration, date, mood, goal, notes, prediction)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["activity"],
        data["category"],
        data["duration"],
        data["date"],
        data["mood"],
        data["goal"],
        data["notes"],
        "Pending"
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Activity stored successfully"})

# ---------- MAIN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
