# Panic Vision - AI Crowd Panic Detection System

## Overview

An intelligent surveillance system that detects crowd density and predicts panic situations using **Computer Vision and Artificial Intelligence**.
It analyzes images and videos in real-time and alerts authorities during abnormal crowd conditions.

---

## Objectives

* Monitor crowded environments
* Detect high-density crowd situations
* Predict panic conditions early
* Provide real-time alerts and logs

---

## Problem 

Traditional CCTV systems only record video and rely on manual monitoring, making it difficult to detect sudden crowd surges or panic situations in real time. This delay in identifying dangerous conditions can lead to serious incidents such as stampedes, injuries, and loss of life, especially in crowded public environments.

## Solution 

To solve this, we developed an AI Crowd Panic Detection System that uses computer vision and a YOLO deep learning model to automatically detect people and analyze crowd density in real time. The system classifies risk levels and instantly triggers alerts through notifications and alarms when a critical threshold is reached, enabling faster response and improving public safety.

## Technologies Used

* Python
* OpenCV
* YOLOv8 (Ultralytics)
* Flask (Web Framework)
* SQLite (Database)
* HTML, CSS (Frontend)
* Telegram (API)
---

##  Features

-  Real-time human detection
-  Crowd density analysis
-  Panic alert system
-  Image & video upload detection
-  User authentication (Login/Register)
-  Telegram alert integration
-  Automatic siren activation
-  Detection history tracking

---

##  System Workflow

1. User uploads image/video
2. YOLO model detects people
3. Crowd count is calculated
4. System determines crowd status
5. Alert triggered if threshold exceeded
6. Data stored in database
7. Results shown on dashboard

---


## Installation

### Clone Repository

```
git clone https://github.com/Aniltingirikari/PanicVision.git
```

### Install Dependencies

```
pip install -r requirements.txt
```

---

## Run the Project

```
python app.py
```

Open in browser:

```
http://127.0.0.1:5000
```



## Future Improvements

* Live CCTV camera integration
* Mobile app alerts
* AI-based behavior prediction
* Cloud deployment

---

## Author

[Tingirikari Anil]

---



