from flask import Flask, render_template, request, redirect, session, jsonify, flash
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)
app.secret_key = "super_secret_key"

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


# -------- SIGNUP ROUTE --------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password)
            )
            conn.commit()
            conn.close()
            return redirect("/login")
        except sqlite3.IntegrityError:
            conn.close()
            return "Email already exists!"

    return render_template("signup.html")

#------ LOGIN ROUTE -------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["user_id"]
            return redirect("/data")
        else:
            flash("Invalid Email or Password")
            return redirect("/login")
        
    return render_template("login.html")

@app.route("/data")
def data_page():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("data.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html") 

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/")
def home():
    return render_template("index.html")

# ---------- MAIN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)


app = Flask(__name__)
CORS(app)
app.secret_key = "super_secret_key"

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
