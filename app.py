from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import cv2
import numpy as np
from ultralytics import YOLO
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import threading

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key")

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "static/outputs"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULT_FOLDER"] = RESULT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# ---------------- TELEGRAM CONFIG ----------------
BOT_TOKEN = "8645196291:AAHdr8uv9cxWumOiYQIqTIwCF6N5XCvX9ns"
CHAT_ID = "2123398010"

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot8645196291:AAHdr8uv9cxWumOiYQIqTIwCF6N5XCvX9ns/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data)
    except:
        pass

# ---------------- SIREN ----------------
def play_siren():
    def sound():
        try:
            os.system("start siren.mp3")  # Windows
        except:
            pass
    threading.Thread(target=sound).start()

# ---------------- LIVE DATA ----------------
live_data = {"people": 0, "panic": "SAFE"}

@app.route("/live_data")
def get_live_data():
    return jsonify(live_data)

# ---------------- LOAD MODEL ----------------
model = YOLO("yolov8n.pt")
PANIC_THRESHOLD = 15

# ---------------- DATABASE ----------------
DATABASE = "app.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        people INTEGER,
        status TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN REQUIRED ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# ---------------- CROWD STATUS ----------------
def crowd_status(count):
    if count <= 5:
        return "LOW CROWD"
    elif count <= 10:
        return "MEDIUM CROWD"
    elif count <= 15:
        return "HIGH CROWD"
    else:
        return "PANIC ALERT 🚨"

# ---------------- SAVE LOG ----------------
def save_log(filename, people, status):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (filename, people, status) VALUES (?, ?, ?)",
        (filename, people, status)
    )
    conn.commit()
    conn.close()

# ---------------- ROUTES ----------------

@app.route("/")
@login_required
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
            conn.commit()
        except:
            conn.close()
            return render_template("register.html", error="User already exists")

        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT username, password FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user"] = user[0]
            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ---------------- IMAGE ----------------
@app.route("/image")
@login_required
def image():
    return render_template("image_detection.html")

@app.route("/image_detect", methods=["POST"])
@login_required
def image_detect():
    file = request.files.get("image")

    if not file or file.filename == "":
        return "No Image Uploaded"

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    results = model(filepath)

    people_count = 0
    for box in results[0].boxes:
        cls = int(box.cls[0])
        if model.names[cls] == "person":
            people_count += 1

    status = crowd_status(people_count)

    # 🚨 ALERT
    if "PANIC" in status:
        play_siren()
        send_telegram_alert(f"🚨 PANIC ALERT!\nPeople Count: {people_count}")

    output_path = os.path.join(RESULT_FOLDER, "output.jpg")
    results[0].save(filename=output_path)

    save_log(file.filename, people_count, status)

    return render_template(
        "image_detection.html",
        result_image=output_path,
        people_count=people_count,
        panic_status=status
    )

# ---------------- VIDEO ----------------
@app.route("/video")
@login_required
def video():
    return render_template("video_detection.html")

@app.route("/video_detect", methods=["POST"])
@login_required
def video_detect():

    video = request.files.get("video")

    if not video or video.filename == "":
        return redirect(url_for("video"))

    input_path = os.path.join(UPLOAD_FOLDER, video.filename)
    output_filename = "processed_" + video.filename
    output_path = os.path.join("static/outputs", output_filename)

    video.save(input_path)

    cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        return "Error opening video"

    frame_width, frame_height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    out = cv2.VideoWriter(output_path, fourcc, 10, (frame_width, frame_height))

    max_people = 0
    alert_sent = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (frame_width, frame_height))
        results = model(frame, conf=0.3)

        people_count = 0
        annotated_frame = frame.copy()

        for box in results[0].boxes:
            cls = int(box.cls[0])
            if model.names[cls] == "person":
                people_count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        status = crowd_status(people_count)

        # 🔴 LIVE UPDATE
        live_data["people"] = people_count
        live_data["panic"] = status

        # 🚨 ALERT (only once)
        if "PANIC" in status and not alert_sent:
            play_siren()
            send_telegram_alert(f"🚨 PANIC ALERT!\nPeople Count: {people_count}")
            alert_sent = True

        if people_count > max_people:
            max_people = people_count

        out.write(annotated_frame)

    cap.release()
    out.release()

    final_status = crowd_status(max_people)
    save_log(video.filename, max_people, final_status)

    return render_template(
        "video_detection.html",
        people_count=max_people,
        message=final_status,
        output_video=url_for("static", filename="outputs/" + output_filename)
    )

# ---------------- LOGS ----------------
@app.route("/logs")
@login_required
def logs():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC")
    log_data = cursor.fetchall()
    conn.close()

    return render_template("logs.html", logs=log_data)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM logs")
    total_logs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT people, timestamp FROM logs ORDER BY timestamp DESC LIMIT 10")
    data = cursor.fetchall()

    conn.close()

    people_counts = [row[0] for row in data][::-1]
    timestamps = [row[1] for row in data][::-1]

    last_status = "No Data"
    if people_counts:
        last_status = crowd_status(people_counts[-1])

    return render_template(
        "dashboard.html",
        threshold=PANIC_THRESHOLD,
        last_status=last_status,
        total_logs=total_logs,
        total_users=total_users,
        timestamps=timestamps,
        people_counts=people_counts
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)