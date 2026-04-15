# 🚨 AI Crowd Panic Detection System

## 📌 Overview

An intelligent surveillance system that detects crowd density and predicts panic situations using **Computer Vision and Artificial Intelligence**.
It analyzes images and videos in real-time and alerts authorities during abnormal crowd conditions.

---

## 🎯 Objectives

* Monitor crowded environments
* Detect high-density crowd situations
* Predict panic conditions early
* Provide real-time alerts and logs

---

## 🧠 Technologies Used

* Python
* OpenCV
* YOLOv8 (Ultralytics)
* Flask (Web Framework)
* SQLite (Database)
* HTML, CSS (Frontend)

---

## ⚙️ Features

* 🧍 Real-time human detection
* 📊 Crowd density analysis
* 🚨 Panic alert system
* 📥 Image & video upload detection
* 📈 Dashboard with logs
* 🔐 User authentication (Login/Register)
* 📩 Telegram alert integration

---

## 🏗️ System Workflow

1. User uploads image/video
2. YOLO model detects people
3. Crowd count is calculated
4. System determines crowd status
5. Alert triggered if threshold exceeded
6. Data stored in database
7. Results shown on dashboard

---

## 📁 Project Structure

```
PANICVISION/
│
├── app.py
├── requirements.txt
├── README.md
|
│
├── static/
├── templates/
├── uploads/
|
```

---

## 💻 Installation

### Clone Repository

```
git clone https://github.com/Aniltingirikari/panic-vision.git
cd panic-vision
```

### Install Dependencies

```
pip install -r requirements.txt
```

---

## ▶️ Run the Project

```
python app.py
```

Open in browser:

```
http://127.0.0.1:5000
```



## 🔮 Future Improvements

* Live CCTV camera integration
* Mobile app alerts
* AI-based behavior prediction
* Cloud deployment

---

## 👨‍💻 Author

**Tingirikari Anil**

---

## 📜 License

This project is for educational purposes only.
