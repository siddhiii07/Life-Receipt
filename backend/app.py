from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for
from flask_cors import CORS
from datetime import datetime
import sqlite3
from flask import send_file
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from io import BytesIO 
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("DejaVu", "fonts/DejaVuSans.ttf"))
from pdf import generate_receipt_pdf

app = Flask(__name__)
CORS(app)
app.secret_key = "super_secret_key"

app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_SECURE'] = False

# ---------------- ENERGY SYSTEM ----------------
ENERGY_RULES = {
    "Study": 15,
    "Work": 10,
    "Fitness": 10,
    "Sleep": 7,
    "Reading": 8,
    "Meditation": 12,
    "Personal": 7,
    "Entertainment": -5,
    "Scrolling": -12,
    "Gaming": -8 
}

DB_NAME = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- CREATE TABLES ----------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        energy INTEGER DEFAULT 50,
        streak INTEGER DEFAULT 0,
        last_activity_date TEXT,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1
        )
    """)

    # Activities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
        activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        activity_name TEXT,
        category TEXT,
        duration REAL,
        date TEXT,
        mood TEXT,
        goal TEXT,
        notes TEXT,
        prediction TEXT,
        receipt_id TEXT
        )
    """)

    conn.commit()
    conn.close()

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
            session["email"] = user["email"]   
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
        duration_minutes = int(act["duration"])
        total += duration_minutes
        processed.append({
            "name": act["activity_name"],
            "duration": duration_minutes
        })

   
    # ---------- FETCH STORED RECEIPT ID ----------
    conn = get_db_connection()
    receipt_row = conn.execute(
        """
        SELECT receipt_id FROM activities
        WHERE user_id = ? AND date = ?
        LIMIT 1
        """,
        (user_id, date)
    ).fetchone()
    conn.close()

    receipt_id = receipt_row["receipt_id"] if receipt_row else "N/A"

    return render_template(
        "receipt.html",
        date=date,
        activities=processed,
        total=total,
        receipt_id=receipt_id
    )

@app.route("/game-dashboard")
def game_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db_connection()
    user = conn.execute("""
        SELECT energy, streak, xp, level
        FROM users
        WHERE user_id = ?
    """, (user_id,)).fetchone()
    conn.close()

    # SAFE FALLBACKS (important)
    energy = user["energy"] if user and user["energy"] is not None else 50
    streak = user["streak"] if user and user["streak"] is not None else 0
    xp = user["xp"] if user and user["xp"] is not None else 0
    level = user["level"] if user and user["level"] is not None else 1

    return render_template(
        "game_dashboard.html",
        energy=int(energy),
        streak=int(streak),
        xp=int(xp),
        level=int(level)
    )

# ---------- API TO ADD ACTIVITY ----------
@app.route("/add-activity", methods=["POST"])
def add_activity():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user_id = session["user_id"]

    from datetime import datetime, timedelta

    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # ---------- CHECK EXISTING RECEIPT ----------
        existing_receipt = cursor.execute(
            """
            SELECT receipt_id FROM activities
            WHERE user_id = ? AND date = ?
            LIMIT 1
            """,
            (user_id, data["date"])
        ).fetchone()

        if existing_receipt:
            receipt_id = existing_receipt["receipt_id"]
        else:
            formatted_date = data["date"].replace("-", "")

            receipt_count = cursor.execute(
                """
                SELECT COUNT(DISTINCT date)
                FROM activities
                WHERE user_id = ?
                """,
                (user_id,)
            ).fetchone()[0]

            receipt_number = str(receipt_count + 1).zfill(3)
            receipt_id = f"RCPT-{formatted_date}-U{user_id}-{receipt_number}"

        # ---------- STORE ACTIVITY ----------
        cursor.execute("""
            INSERT INTO activities 
            (user_id, activity_name, category, duration, date, mood, goal, notes, prediction, receipt_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data["activity"],
            data["category"],
            data["duration"],
            data["date"],
            data["mood"],
            data["goal"],
            data["notes"],
            "Pending",
            receipt_id
        ))

        # ---------- ENERGY + STREAK SYSTEM ----------
        duration = int(data["duration"])
        category = data["category"].lower()
        mood = data["mood"].lower()
        today = data["date"]

        energy_gain = 0

        # Duration reward
        if duration >= 90:
            energy_gain += 20
        elif duration >= 60:
            energy_gain += 10
        elif duration >= 30:
            energy_gain += 5

        # Category bonus
        if category in ["workout", "exercise", "gym"]:
            energy_gain += 15
        elif category in ["study", "learning"]:
            energy_gain += 8

        # Mood bonus
        if mood == "happy":
            energy_gain += 5
        elif mood == "productive":
            energy_gain += 7

        # ---------- GET USER DATA ----------
        cursor.execute("""
            SELECT energy, last_activity_date, streak 
            FROM users 
            WHERE user_id = ?
        """, (user_id,))
        
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        current_energy = user["energy"] if user["energy"] else 50
        last_date = user["last_activity_date"]
        streak = user["streak"] if user["streak"] else 0

        today_date = datetime.strptime(today, "%Y-%m-%d")

        if last_date:
            last_date_obj = datetime.strptime(last_date, "%Y-%m-%d")

            if today_date == last_date_obj + timedelta(days=1):
                streak += 1
                energy_gain += 10
            elif today_date == last_date_obj:
                pass
            else:
                streak = 1
        else:
            streak = 1

        new_energy = current_energy + energy_gain
        new_energy = max(0, min(new_energy, 100))

        cursor.execute("""
            UPDATE users
            SET energy = ?, last_activity_date = ?, streak = ?
            WHERE user_id = ?
        """, (
            new_energy,
            today,
            streak,
            user_id
        ))

        conn.commit()

        return jsonify({
            "message": "Activity stored successfully",
            "receipt_id": receipt_id,
            "energy_gained": energy_gain,
            "new_energy": new_energy,
            "streak": streak
        })

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()
# Activity stored
# energy increase smartly
# Streak builds
# Streak bonus applied
# Energy capped at 100
# Safe from crashes
# Returns gamified response

# ---------- DOWNLOAD RECEIPTS ----------
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

    # ---------- convert DB values safely to minutes ----------
    processed = []

    for act in activities:
        raw_duration = act["duration"]

        try:
            raw_duration = float(raw_duration)

            # old data stored as hours (like 1.5) → convert to minutes
            if raw_duration <= 24:
                duration_minutes = int(raw_duration * 60)
            else:
                duration_minutes = int(raw_duration)

        except:
            duration_minutes = 0

        processed.append({
            "activity_name": act["activity_name"],
            "duration": duration_minutes
        })

    # ---------- generate pdf ----------
    pdf_bytes = generate_receipt_pdf(date, processed)

    # ---------- send file ----------
    return send_file(
        BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=f"receipt_{date}.pdf",
        mimetype="application/pdf"
    )

# ---------- MAIN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
    
