# V.I.S.A.G.E

# AI Security Camera Project Documentation

## Description of System (DoS)
The **AI Security Camera** is a smart surveillance system that uses motion detection, face detection, and network communication to monitor a designated area. The camera streams live video, detects motion, identifies human faces, and sends notifications with captured images to the user via **Telegram Bot API**. The system is designed to work autonomously, offering local storage and optional cloud backup capabilities.

---

## Project Overview
### Tech Stack
| Component        | Language/Library       | Description             |
|----------------|----------------------|-----------------------|
| Camera Module   | ESP32-CAM / Webcam | Video Streaming       |
| Backend API     | Flask (Python)     | API for streaming, detection, and commands |
| Motion Detection | OpenCV            | Detects movement in video frames |
| Face Detection   | OpenCV + Haar Cascades | Identifies human faces in video frames |
| Notifications   | Telegram Bot API    | Sends alerts + images to the user |
| Local Storage   | SQLite            | Stores detected faces and timestamps |
| Optional Cloud  | Google Drive API   | Uploads images to the cloud |

---

## System Architecture
```
[ESP32-CAM / Webcam] ---> [Flask API] ---> [Telegram Bot API]
                          |                 |
                  [SQLite DB]       [Cloud Storage (Optional)]
                          |
                   [Face Detection + Motion Detection]
```

---

## Features
- Real-Time Video Streaming
- Motion Detection
- Face Detection
- Telegram Notifications
- Remote ON/OFF Commands via Telegram
- Local Storage
- Optional Cloud Backup

---

## Timeline
| Task                    | Time Estimate | Difficulty |
|-------------------------|---------------|------------|
| Video Streaming + Flask API | 3 Days      | 🔥       |
| Motion Detection        | 4 Days      | 🔥🔥    |
| Face Detection          | 5 Days      | 🔥🔥🔥  |
| Telegram Bot Setup      | 3 Days      | 🔥       |
| Local Storage           | 2 Days      | 🔥       |
| Cloud Backup (Optional)  | 3 Days      | 🔥       |
| Testing + Debugging     | 4 Days      | 🔥🔥    |
| Report Writing          | 4 Days      | 🔥       |

---

## Folder Structure
```
📁 AI_Security_Camera
│
├── backend/
│   ├── app.py               # Flask API
│   ├── camera.py            # Camera Module
│   ├── detector.py          # Motion & Face Detection
│   ├── bot.py               # Telegram Bot API
│   └── storage.py           # Local Storage (SQLite)
│
└── requirements.txt         # Dependencies
```

---

## Technologies Used
- Python
- Flask
- OpenCV
- SQLite
- Telegram Bot API
- ESP32-CAM (Optional)
- Google Drive API (Optional)

---

## Next Steps
1. Set up Flask API + Video Streaming
2. Implement Motion Detection
3. Integrate Face Detection
4. Connect Telegram Bot
5. Store Captured Images Locally
6. Add Cloud Backup
7. Write Report
8. Testing and Debugging

---

Do you want me to generate the **Base Folder + Initial Code Boilerplate + UML Class Diagrams** now?

