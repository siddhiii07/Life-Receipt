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
from tensorflow.keras.models import load_model
import joblib
import numpy as np

# ---------- LOAD LSTM MODEL ----------
lstm_model = load_model("../models/productivity_lstm_model.h5")
mood_encoder = joblib.load("../models/mood_encoder.pkl")
label_encoder = joblib.load("../models/label_encoder.pkl") 

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

# ---------- LSTM PRODUCTIVITY PREDICTION ----------
def predict_productivity(study, workout, entertainment, scrolling, sleep, mood):

    try:
        mood_encoded = mood_encoder.transform([mood])[0]
    except:
        mood_encoded = 0

    features = np.array([
        study,
        workout,
        entertainment,
        scrolling,
        sleep,
        mood_encoded
    ])

    features = features.reshape((1,6,1))

    prediction = lstm_model.predict(features, verbose=0)

    predicted_class = np.argmax(prediction)

    label = label_encoder.inverse_transform([predicted_class])[0]

    return label

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
    today = datetime.today().strftime("%Y-%m-%d")

    conn = get_db_connection()

    user = conn.execute("""
        SELECT energy, streak, xp, level
        FROM users
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    # fetch today's prediction
    prediction_row = conn.execute("""
        SELECT prediction
        FROM activities
        WHERE user_id = ? AND date = ?
        LIMIT 1
    """, (user_id, today)).fetchone()

    conn.close()

    # SAFE FALLBACKS
    energy = user["energy"] if user and user["energy"] is not None else 50
    streak = user["streak"] if user and user["streak"] is not None else 0
    xp = user["xp"] if user and user["xp"] is not None else 0
    level = user["level"] if user and user["level"] is not None else 1

    today_status = prediction_row["prediction"] if prediction_row else None

    return render_template(
        "game_dashboard.html",
        energy=int(energy),
        streak=int(streak),
        xp=int(xp),
        level=int(level),
        today_status=today_status
    )
    
@app.route("/analytics")
def analytics():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db_connection()

    # -------- ACTIVITY DATA --------
    activities = conn.execute("""
        SELECT category, duration
        FROM activities
        WHERE user_id = ?
    """, (user_id,)).fetchall()

    # -------- PRODUCTIVITY DATA --------
    prediction_data = conn.execute("""
        SELECT prediction, COUNT(*) as total
        FROM activities
        WHERE user_id = ?
        GROUP BY prediction
    """, (user_id,)).fetchall()

    # -------- MOOD DATA --------
    mood_data = conn.execute("""
        SELECT mood, COUNT(*) as total
        FROM activities
        WHERE user_id = ?
        GROUP BY mood
    """, (user_id,)).fetchall()

    conn.close()

    # -------- ACTIVITY TOTALS --------
    study = 0
    fitness = 0
    entertainment = 0
    scrolling = 0

    for act in activities:

        cat = act["category"].lower()
        dur = float(act["duration"])

        if cat == "study":
            study += dur

        elif cat in ["fitness","gym","exercise"]:
            fitness += dur

        elif cat in ["entertainment","gaming"]:
            entertainment += dur

        elif cat == "scrolling":
            scrolling += dur

    # -------- PRODUCTIVITY COUNTS --------
    productive = 0
    leisure = 0

    for row in prediction_data:

        if row["prediction"] == "Productive":
            productive = row["total"]

        elif row["prediction"] == "Leisure":
            leisure = row["total"]

    # -------- MOOD COUNTS --------
    moods = {}
    for row in mood_data:
        moods[row["mood"]] = row["total"]

    return render_template(
        "analytics.html",
        study=study,
        fitness=fitness,
        entertainment=entertainment,
        scrolling=scrolling,
        productive=productive,
        leisure=leisure,
        moods=moods
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

        # ---------- ENERGY SYSTEM ----------
        duration = int(data["duration"])
        category = data["category"].lower()
        mood = data["mood"].lower()

        activity_date = data["date"]
        today = datetime.today().strftime("%Y-%m-%d")

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

        xp_gain = energy_gain

        # ---------- GET USER DATA ----------
        cursor.execute("""
            SELECT energy, last_activity_date, streak, xp, level 
            FROM users 
            WHERE user_id = ?
        """, (user_id,))
        
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        current_energy = user["energy"] if user["energy"] else 30
        last_date = user["last_activity_date"]
        streak = user["streak"] if user["streak"] else 0
        current_xp = user["xp"] if user["xp"] else 0
        current_level = user["level"] if user["level"] else 1

        # ---------- ONLY UPDATE STATS IF ACTIVITY IS TODAY ----------
        if activity_date == today:

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

            # ----- XP SYSTEM -----
            new_xp = current_xp + xp_gain
            new_level = current_level

            level_threshold = 100

            if new_xp >= level_threshold:
                new_level += 1
                new_xp -= level_threshold

        else:
            # Past activity → do not change stats
            new_energy = current_energy
            new_xp = current_xp
            new_level = current_level

        # ---------- UPDATE USER ----------
        cursor.execute("""
            UPDATE users
            SET energy = ?, last_activity_date = ?, streak = ?, xp = ?, level = ?
            WHERE user_id = ?
        """, (
            new_energy,
            activity_date,
            streak,
            new_xp,
            new_level,
            user_id
        ))
        
                # ---------- LSTM DAILY PRODUCTIVITY PREDICTION ----------
        day_activities = cursor.execute("""
            SELECT category, duration
            FROM activities
            WHERE user_id = ? AND date = ?
        """, (user_id, data["date"])).fetchall()

        study = 0
        workout = 0
        entertainment = 0
        scrolling = 0
        sleep = 420

        for act in day_activities:

            cat = act["category"].lower()
            dur = float(act["duration"])

            if cat == "study":
                study += dur

            elif cat in ["fitness","gym","exercise","workout"]:
                workout += dur

            elif cat in ["entertainment","gaming","netflix"]:
                entertainment += dur

            elif cat in ["scrolling","social media"]:
                scrolling += dur

        prediction = predict_productivity(
            study,
            workout,
            entertainment,
            scrolling,
            sleep,
            data["mood"]
        )

        # update prediction for today's activities
        cursor.execute("""
            UPDATE activities
            SET prediction = ?
            WHERE user_id = ? AND date = ?
        """, (prediction, user_id, data["date"]))

        conn.commit()

        return jsonify({
            "receipt_id": receipt_id,
            "message": "Activity stored successfully",
            "energy_gained": energy_gain,
            "xp_gained": xp_gain,
            "new_energy": new_energy,
            "new_xp": new_xp,
            "level": new_level,
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
    
