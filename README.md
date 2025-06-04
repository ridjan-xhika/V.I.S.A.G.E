Below is a suggested **MIT LICENSE** file, followed by a revamped, eye-catching **README.md**. Adjust any placeholders (e.g., year or author) as needed.

---

## LICENSE (MIT)

```
MIT License

Copyright (c) 2025 Ridjan Xhika

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights 
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
copies of the Software, and to permit persons to whom the Software is 
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in 
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
SOFTWARE.
```

---

<p align="center">
  <img src="https://raw.githubusercontent.com/yourusername/VISAGE-Telegram-Bot/main/assets/logo.png" alt="V.I.S.A.G.E Logo" width="200">
</p>

<h1 align="center">V.I.S.A.G.E</h1>
<p align="center">
  <strong>AI-Powered Security Camera System</strong>  
  <br>
  <a href="#features">Features</a> • 
  <a href="#system-architecture">Architecture</a> • 
  <a href="#setup">Setup & Installation</a> • 
  <a href="#usage">Usage</a> • 
  <a href="#contributing">Contributing</a> • 
  <a href="#license">License</a>
</p>

---

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python Version">
  <img src="https://img.shields.io/badge/flask-%3E%3D2.0-green" alt="Flask">
  <img src="https://img.shields.io/badge/opencv-%3E%3D4.0-yellow" alt="OpenCV">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
</p>

---

## 🎯 Project Overview

**V.I.S.A.G.E** (Visual Intelligent Surveillance And Guardian Engine) is an AI-driven security camera platform designed for real-time monitoring, motion detection, face recognition, and instant notifications. Leveraging a lightweight Flask backend, OpenCV detection pipelines, and the Telegram Bot API, V.I.S.A.G.E empowers you to:

* 🚀 Stream live video from ESP32-CAM or a standard USB webcam.
* 🕵️‍♂️ Detect motion with configurable sensitivity and threshold.
* 🧑‍🤝‍🧑 Identify faces using Haar cascades and store snapshots locally (and optionally in the cloud).
* 📲 Receive instant alerts (with images) via Telegram Bot.
* 🔌 Control the camera remotely (ON/OFF, snapshots, video clips) through chat commands.
* 💾 Log all detections in a local SQLite database, with optional Google Drive backup.

Properly modularized, this system can be extended to other APIs, cloud services, or hardware platforms.

---

## 🔥 Key Features

| Category             | Details                                                                                  |
| -------------------- | ---------------------------------------------------------------------------------------- |
| **Video Streaming**  | ESP32-CAM or USB webcam → Flask application → MJPEG stream (HTTP endpoint)               |
| **Motion Detection** | OpenCV MOG2 → fast, scalable background subtraction → customizable sensitivity/threshold |
| **Face Detection**   | OpenCV Haar cascades → draw bounding boxes → store snapshots + timestamps                |
| **Notifications**    | Telegram Bot API → real-time alerts → supports single/multiple admin users               |
| **Remote Control**   | `/start`, `/status`, `/snapshot`, `/video`, `/settings` (via Telegram chat)              |
| **Local Storage**    | SQLite database → logs faces + motion timestamps → quick search/retrieval                |
| **Cloud Backup**     | (Optional) Google Drive API → upload captured images → secure off-site storage           |
| **Extensibility**    | Modular codebase → easily add new detection algorithms (e.g., deep learning models)      |

---

## 🏗️ System Architecture

```
┌───────────────────┐       ┌───────────────────────────────────┐       ┌────────────────────────┐
│                   │       │                                   │       │                        │
│  ESP32-CAM /      │───▶   │      Flask Backend (app.py)       │───▶   │  Telegram Bot API      │
│  USB Webcam       │       │  ┌──────────────────────────────┐ │       │  (bot.py)              │
│  (video feed)     │       │  │  Detector Module (detector.py) │ │       │                        │
│                   │       │  └──────────────────────────────┘ │       │                        │
│                   │       │          │                         │       │                        │
│                   │       │          ▼                         │       │                        │
│                   │       │  ┌──────────────────────────────┐ │       │                        │
│                   │       │  │   Storage Module (storage.py) │ │       │                        │
│                   │       │  └──────────────────────────────┘ │       │                        │
│                   │       │          │                         │       │                        │
│                   │       │          ▼                         │       │                        │
│                   │       │  ┌──────────────────────────────┐ │       │                        │
│                   │       │  │    SQLite Database (local)    │ │       │                        │
│                   │       │  └──────────────────────────────┘ │       │                        │
│                   │       │          │                         │       │                        │
│                   │       │          ▼                         │       │                        │
│                   │       │  ┌──────────────────────────────┐ │       │                        │
│                   │       │  │ Google Drive API (optional)    │ │       │                        │
│                   │       │  └──────────────────────────────┘ │       │                        │
└───────────────────┘       └───────────────────────────────────┘       └────────────────────────┘
```

1. **Camera Module (`camera.py`)**
   Handles live capture (ESP32-CAM or USB), frame buffering, and optional overlays (timestamp, motion boxes, etc.).

2. **Detector Module (`detector.py`)**

   * **Motion Detection**: Background subtraction (MOG2), contour analysis → returns bounding rectangles.
   * **Face Detection**: Haar cascade classifiers → stores detected faces + their timestamps.

3. **Storage Module (`storage.py`)**

   * **SQLite DB**: Tables for motion events + face snapshots (path, timestamp, metadata).
   * **Cloud Backup (Optional)**: Google Drive uploader → automatically pushes new images.

4. **Flask API (`app.py`)**

   * **Endpoints**:

     * `/stream` → MJPEG live stream
     * `/snapshot` → Single JPEG capture
     * `/toggle_motion` → Enable/disable motion detection
     * Additional RESTful endpoints (config, stats, etc.)

5. **Telegram Bot (`bot.py`)**

   * **Commands**: `/start`, `/status`, `/snapshot`, `/video`, `/settings`, `/help`
   * **Alerts**: Pushes motion/face snapshots to authorized users.
   * **Security**: Validates user IDs against a whitelist (stored in environment variables).

---

## 🚀 Getting Started

### Prerequisites

* **Hardware**:

  * ESP32-CAM (optional) or standard USB webcam
  * Raspberry Pi / Linux / Windows / macOS
* **Software**:

  * Python 3.8 or higher
  * (Optional) Google Drive API credentials for cloud backup

### Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/VISAGE-Security-Camera.git
   cd VISAGE-Security-Camera
   ```

2. **Create & Activate Virtual Environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. **Install Python Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the project root with:

   ```
   # Telegram Bot
   BOT_TOKEN=your_telegram_bot_token
   ADMIN_CHAT_ID=123456789

   # Flask API
   FLASK_APP=backend/app.py
   FLASK_ENV=production
   VISAGE_API_URL=http://localhost:5000

   # (Optional) Google Drive
   GDRIVE_CREDENTIALS_JSON=/path/to/credentials.json
   GDRIVE_FOLDER_ID=your_folder_id
   ```

5. **Initialize Database**

   ```bash
   cd backend
   python storage.py --init-db
   cd ..
   ```

6. **Start the Flask API**

   ```bash
   cd backend
   flask run --host=0.0.0.0 --port=5000
   cd ..
   ```

7. **Launch the Telegram Bot** (in a separate terminal)

   ```bash
   cd backend
   python bot.py
   ```

> **Tip:** If you need the ESP32-CAM to stream into Flask, follow [this ESP32-CAM guide](https://randomlink.example.com/esp32-cam-streaming) to configure its MJPEG endpoint and update `app.py` accordingly.

---

## 📱 Usage

Once both Flask and the Telegram Bot are running:

1. **Access Live Stream**
   Open a browser and navigate to:

   ```
   http://<your_server_ip>:5000/stream
   ```

   (Replace `<your_server_ip>` with `localhost` or your machine’s IP.)

2. **Interact via Telegram**

   * Search for your bot (by its name) in Telegram.
   * Send `/start` to see available commands.
   * Example:

     * `/status` → Returns system uptime, motion status, face counts.
     * `/snapshot` → Bot replies with the latest camera snapshot.
     * `/video` → Bot records a 5-second clip and sends it.
     * `/settings` → Bot shows a custom keyboard to toggle motion sensitivity, threshold, etc.

3. **View Alerts & Logs**

   * Each motion or face detection triggers a push notification (with image) to your Telegram.
   * All events are logged in `backend/visage.db` (SQLite). Use `sqlite3 visage.db` to inspect.

---

## 🎨 Example Screenshots

<p align="center">
  <img src="https://raw.githubusercontent.com/yourusername/VISAGE-Security-Camera/main/assets/snapshot_example.jpg" alt="Snapshot Example" width="500">
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/yourusername/VISAGE-Security-Camera/main/assets/telegram_alert.jpg" alt="Telegram Alert" width="500">
</p>

---

## 🛠️ Configuration Options

| Option                  | Description                                       | Default     |
| ----------------------- | ------------------------------------------------- | ----------- |
| `VIDEO_WIDTH`           | Camera capture width (px)                         | `320`       |
| `VIDEO_HEIGHT`          | Camera capture height (px)                        | `240`       |
| `TARGET_FPS`            | Desired frame rate for streaming/detection        | `60`        |
| `MOTION_THRESHOLD`      | Minimum area (in px²) for motion to trigger alert | `500`       |
| `MOTION_SENSITIVITY`    | Background subtractor learning rate (1–100)       | `25`        |
| `MOTION_CHECK_INTERVAL` | Skip N–1 frames between motion checks             | `2`         |
| `DB_PATH`               | Path to SQLite database file                      | `visage.db` |
| `GDRIVE_BACKUP_ENABLED` | `true`/`false` to enable automatic Google Drive   | `false`     |

These can be set in `.env`, or adjusted in each module’s constructor. See comments in `app.py` and `camera.py` for details.

---

## 📈 Monitoring & Statistics

From the Flask API, you can fetch runtime stats:

* **Endpoint:**

  ```
  GET /api/stats
  ```
* **Response Example:**

  ```json
  {
    "frame_count": 12500,
    "error_count": 0,
    "actual_fps": 58.3,
    "target_fps": 60,
    "is_running": true,
    "camera_open": true,
    "motion_detection_enabled": true,
    "motion_detected": false,
    "motion_areas_count": 0,
    "last_motion_time": 0,
    "uptime": 3600.5,
    "width": 320,
    "height": 240
  }
  ```

You can build dashboards or integrate Prometheus/Grafana if needed.

---

## 🧑‍🤝‍🧑 Contributing

We welcome any enhancements, bug fixes, or new features! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Install dependencies** (inside a virtual environment)

   ```bash
   pip install -r requirements.txt
   ```
4. **Make your changes**, include tests or examples if applicable.
5. **Run existing tests** (if you add tests, place them under `backend/tests/`)
6. **Commit & push**

   ```bash
   git add .
   git commit -m "Describe your change"
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request** with a clear description of what you’ve added/changed.

> **Code Style:**
>
> * Follow PEP 8 for Python.
> * Use descriptive variable/function names and docstrings.
> * Keep each module focused (SRP – Single Responsibility Principle).

---

## 📜 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

👤 **Author**
Ridjan Xhika – [ridjan.xhika@epitech.eu](mailto:ridjan.xhika@epitech.eu)

*Project “V.I.S.A.G.E” © 2025 Ridjan Xhika. All rights reserved.*
