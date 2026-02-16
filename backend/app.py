from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for
from flask_cors import CORS
from datetime import datetime
import sqlite3
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from io import BytesIO 

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
    print("SESSION:", dict(session))
    print("USER ID:", session.get("user_id"))

    if "user_id" not in session:
        print("NO USER ID FOUND")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO activities 
        (activity_name, category, duration, date, mood, goal, notes, prediction, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["activity"],
        data["category"],
        data["duration"],
        data["date"],
        data["mood"],
        data["goal"],
        data["notes"],
        "Pending",
        session["user_id"]
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
            session["email"] = user["email"]   # 👈 ADD THIS
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid Email or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


"""@app.route("/data")
def data_page():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("data.html")"""

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/my-receipts")
def my_receipts():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db_connection()
    dates = conn.execute(
        """
        SELECT DISTINCT date 
        FROM activities 
        WHERE user_id = ?
        ORDER BY date DESC
        """,
        (user_id,)
    ).fetchall()
    conn.close()

    return render_template("my_receipts.html", dates=dates)

# Individual Receipt Page
@app.route("/receipt/<date>")
def receipt(date):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db_connection()
    activities = conn.execute(
        """
        SELECT activity_name, duration
        FROM activities
        WHERE date = ? AND user_id = ?
        """,
        (date, user_id)
    ).fetchall()
    conn.close()

    processed = []
    total = 0

    for act in activities:
        duration_hours = float(act["duration"])   # DB stores hours
        duration_minutes = int(duration_hours * 60)

        total += duration_minutes

        processed.append({
            "name": act["activity_name"],
            "duration": duration_minutes
        })

    return render_template(
        "receipt.html",
        date=date,
        activities=processed,
        total=total
    )

@app.route("/download-receipt/<date>")
def download_receipt(date):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db_connection()
    activities = conn.execute(
        """
        SELECT activity_name, duration
        FROM activities
        WHERE date = ? AND user_id = ?
        """,
        (date, user_id)
    ).fetchall()
    conn.close()

    if not activities:
        return "No activities found", 404

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>Daily Activity Receipt</b>", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(f"Date: {date}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    total = 0

    for act in activities:
        duration_minutes = int(float(act["duration"]) * 60)
        total += duration_minutes

        hours = duration_minutes // 60
        minutes = duration_minutes % 60

        elements.append(
            Paragraph(
                f"{act['activity_name']} - {hours}h {minutes}m",
                styles["Normal"]
            )
        )

    elements.append(Spacer(1, 0.3 * inch))

    total_hours = total // 60
    total_minutes = total % 60

    elements.append(
        Paragraph(
            f"<b>Total: {total_hours}h {total_minutes}m</b>",
            styles["Normal"]
        )
    )

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"receipt_{date}.pdf",
        mimetype="application/pdf"
    )

# ---------- MAIN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)

# ---------- API TO ADD ACTIVITY ----------
@app.route("/add-activity", methods=["POST"])
def add_activity():
    print("SESSION:", session)   # 👈 add this

    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

@app.route("/download-receipt/<date>")
def download_receipt(date):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db_connection()
    activities = conn.execute(
        """
        SELECT activity_name, duration
        FROM activities
        WHERE date = ? AND user_id = ?
        """,
        (date, user_id)
    ).fetchall()
    conn.close()

    if not activities:
        return "No activities found", 404

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>Daily Activity Receipt</b>", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(f"Date: {date}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    total = 0

    for act in activities:
        duration = int(act["duration"])
        total += duration

        hours = duration // 60
        minutes = duration % 60

        elements.append(
            Paragraph(
                f"{act['activity_name']} - {hours}h {minutes}m",
                styles["Normal"]
            )
        )

    elements.append(Spacer(1, 0.3 * inch))

    total_hours = total // 60
    total_minutes = total % 60

    elements.append(
        Paragraph(
            f"<b>Total: {total_hours}h {total_minutes}m</b>",
            styles["Normal"]
        )
    )

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"receipt_{date}.pdf",
        mimetype="application/pdf"
    ) 
    
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