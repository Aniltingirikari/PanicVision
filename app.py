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
import platform
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key_change_this_in_production")

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "static/outputs"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULT_FOLDER"] = RESULT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB max file size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# ---------------- TELEGRAM CONFIG ----------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    """Send alert via Telegram bot"""
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Telegram alerts disabled: Missing credentials in .env file")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID, 
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Telegram alert sent successfully!")
            return True
        else:
            print(f"❌ Telegram alert failed! Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram alert error: {e}")
        return False

# ---------------- SIREN ----------------
def play_siren():
    """Play siren sound automatically when panic is detected"""
    def sound():
        try:
            siren_file = os.path.join("static", "sounds", "siren.mp3")
            
            if not os.path.exists(siren_file):
                print(f"⚠️ Siren file not found: {siren_file}")
                return
            
            system = platform.system()
            
            if system == "Windows":
                import winsound
                winsound.PlaySound(siren_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            elif system == "Darwin":  # macOS
                os.system(f"afplay {siren_file} &")
            else:  # Linux
                os.system(f"aplay {siren_file} &")
                
            print("🔊 Siren playing!")
            
        except Exception as e:
            print(f"Siren error: {e}")
    
    threading.Thread(target=sound, daemon=True).start()

# ---------------- LIVE DATA ----------------
live_data = {"people": 0, "panic": "SAFE", "timestamp": ""}

@app.route("/live_data")
def get_live_data():
    return jsonify(live_data)

# ---------------- LOAD MODEL ----------------
try:
    model = YOLO("yolov8n.pt")
    print("✅ YOLO model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load YOLO model: {e}")
    model = None

PANIC_THRESHOLD = 15

# ---------------- DATABASE ----------------
DATABASE = "app.db"

def init_db():
    """Initialize database with tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
    print("✅ Database initialized")

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
    """Determine crowd status based on person count"""
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
    """Save detection log to database"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs (filename, people, status) VALUES (?, ?, ?)",
            (filename, people, status)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving log: {e}")
        return False

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
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        if not username or not email or not password:
            return render_template("register.html", error="All fields are required")
        
        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters")
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? OR username=?", (email, username))
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return render_template("register.html", error="Username or email already exists")
        
        hashed_password = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                      (username, email, hashed_password))
        conn.commit()
        conn.close()
        
        return render_template("register.html", success="Account created successfully! Please login.")
    
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
        else:
            return render_template("login.html", error="Invalid email or password")
    
    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ---------------- IMAGE DETECTION ----------------
@app.route("/image")
@login_required
def image():
    return render_template("image_detection.html")

@app.route("/image_detect", methods=["POST"])
@login_required
def image_detect():
    if not model:
        return "Model not loaded. Please check server logs.", 500
    
    file = request.files.get("image")

    if not file or file.filename == "":
        return "No Image Uploaded", 400
    
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        return "Invalid image format. Please upload JPG, JPEG, PNG, or BMP.", 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        results = model(filepath)
        people_count = 0
        for box in results[0].boxes:
            cls = int(box.cls[0])
            if model.names[cls] == "person":
                people_count += 1
    except Exception as e:
        print(f"Error processing image: {e}")
        return "Error processing image", 500

    status = crowd_status(people_count)

    if "PANIC" in status:
        print(f"🔴 PANIC DETECTED! People: {people_count}")
        play_siren()
        
        alert_message = f"""🚨 PANIC ALERT DETECTED! 🚨

📍 Source: Image Detection
📁 File: {file.filename}
👥 People Count: {people_count}
⚠️ Status: {status}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔊 Siren activated automatically!
🔔 Immediate action required!"""
        
        send_telegram_alert(alert_message)
        live_data["panic"] = status
        live_data["timestamp"] = datetime.now().isoformat()

    output_filename = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    output_path = os.path.join(RESULT_FOLDER, output_filename)
    results[0].save(filename=output_path)

    save_log(file.filename, people_count, status)

    return render_template(
        "image_detection.html",
        result_image=output_path,
        people_count=people_count,
        panic_status=status
    )

# ---------------- VIDEO DETECTION ----------------
@app.route("/video")
@login_required
def video():
    return render_template("video_detection.html")

@app.route("/video_detect", methods=["POST"])
@login_required
def video_detect():
    if not model:
        return "Model not loaded. Please check server logs.", 500

    video = request.files.get("video")

    if not video or video.filename == "":
        return redirect(url_for("video"))

    allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    file_ext = os.path.splitext(video.filename)[1].lower()
    if file_ext not in allowed_extensions:
        return "Invalid video format. Please upload MP4, AVI, MOV, MKV, or WEBM.", 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    input_filename = f"input_{timestamp}_{video.filename}"
    output_filename = f"processed_{timestamp}.mp4"
    
    input_path = os.path.join(UPLOAD_FOLDER, input_filename)
    output_path = os.path.join("static/outputs", output_filename)

    video.save(input_path)
    print(f"📹 Video saved: {input_path}")

    try:
        cap = cv2.VideoCapture(input_path)

        if not cap.isOpened():
            return "Error opening video file", 400

        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        if frame_width > 1280:
            scale = 1280 / frame_width
            frame_width = 1280
            frame_height = int(frame_height * scale)
        
        frame_width = frame_width if frame_width % 2 == 0 else frame_width + 1
        frame_height = frame_height if frame_height % 2 == 0 else frame_height + 1
        
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_path, fourcc, min(fps, 15), (frame_width, frame_height))

        max_people = 0
        alert_sent = False
        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            
            if frame_count % 2 != 0:
                continue

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
                    
                    conf = float(box.conf[0])
                    label = f"Person {conf:.2f}"
                    cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            status = crowd_status(people_count)
            
            if "PANIC" in status:
                text_color = (0, 0, 255)
            elif "HIGH" in status:
                text_color = (0, 165, 255)
            elif "MEDIUM" in status:
                text_color = (0, 255, 255)
            else:
                text_color = (0, 255, 0)
            
            cv2.putText(annotated_frame, f"People: {people_count}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)
            cv2.putText(annotated_frame, f"Status: {status}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)

            live_data["people"] = people_count
            live_data["panic"] = status

            if "PANIC" in status and not alert_sent:
                print(f"🔴 PANIC DETECTED IN VIDEO! People: {people_count}")
                play_siren()
                
                alert_message = f"""🚨 PANIC ALERT DETECTED! 🚨

📍 Source: Video Detection
📁 File: {video.filename}
👥 People Count: {people_count}
⚠️ Status: {status}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔊 Siren activated automatically!
🔔 Emergency situation detected!"""
                
                send_telegram_alert(alert_message)
                alert_sent = True

            if people_count > max_people:
                max_people = people_count

            out.write(annotated_frame)
            
            if frame_count % 50 == 0:
                print(f"Processing: {frame_count}/{total_frames} frames")

        cap.release()
        out.release()
        os.remove(input_path)
        
        print(f"✅ Video processing complete!")
        print(f"   Max people: {max_people}")

    except Exception as e:
        print(f"Error processing video: {e}")
        import traceback
        traceback.print_exc()
        return f"Error processing video: {str(e)}", 500

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
    cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 100")
    log_data = cursor.fetchall()
    conn.close()

    return render_template("logs.html", logs=log_data)

# ---------------- CLEANUP ----------------
@app.route("/cleanup", methods=["POST"])
@login_required
def cleanup():
    """Clean up old files"""
    try:
        for file in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        outputs = sorted([f for f in os.listdir(RESULT_FOLDER) if f.endswith(('.jpg', '.mp4'))])
        for old_file in outputs[:-50]:
            os.remove(os.path.join(RESULT_FOLDER, old_file))
            
        return jsonify({"success": True, "message": "Cleanup completed"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ---------------- ERROR HANDLERS ----------------
@app.errorhandler(404)
def not_found(error):
    return "<h1>404 - Page Not Found</h1><p>The page you are looking for does not exist.</p>", 404

@app.errorhandler(500)
def internal_error(error):
    return "<h1>500 - Internal Server Error</h1><p>Something went wrong. Please try again later.</p>", 500

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)