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

# V.I.S.A.G.E Telegram Bot

## Overview
The **V.I.S.A.G.E Telegram Bot** serves as the user interface for the **V.I.S.A.G.E AI Security Camera** system. It allows remote interaction, real-time alerts, and system control via Telegram, ensuring seamless monitoring and security management.

## Features
- **User Authentication**: Only authorized users can control the security system.
- **Live Alerts**: Sends notifications for detected motion or unrecognized faces.
- **Camera Control**: Start, stop, and configure camera settings via chat commands.
- **Image/Video Retrieval**: Request snapshots or video clips directly from Telegram.
- **Multi-User Support**: Can be configured for multiple admins and users.

## Requirements
Ensure you have the following dependencies installed:

- Python 3.8+
- `python-telegram-bot` (`pip install python-telegram-bot`)
- `opencv-python` (`pip install opencv-python`)
- `numpy` (`pip install numpy`)
- `requests` (`pip install requests`)
- **V.I.S.A.G.E System API** (Ensure the backend is running)

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/VISAGE-Telegram-Bot.git
   cd VISAGE-Telegram-Bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file and add your **Telegram Bot Token**:
   ```
   BOT_TOKEN=your_telegram_bot_token
   VISAGE_API_URL=http://your-visage-api-endpoint
   ADMIN_CHAT_ID=your_telegram_chat_id
   ```

4. Run the bot:
   ```bash
   python bot.py
   ```

## Usage
### Commands
- `/start` – Initialize the bot and display available commands.
- `/status` – Get the current status of the V.I.S.A.G.E system.
- `/snapshot` – Capture and send a snapshot from the camera.
- `/video` – Record and send a short video.
- `/settings` – Adjust V.I.S.A.G.E system configurations.
- `/help` – Show command descriptions.

## Deployment
For continuous operation, you can run the bot as a background service:
```bash
nohup python bot.py &
```
Or use a process manager like `systemd` or `pm2`.

## Security
- Only authorized users should have access to the bot.
- Store sensitive credentials in environment variables or a `.env` file.
- Ensure the V.I.S.A.G.E API is secured with authentication.

## Contributing
Feel free to submit pull requests or report issues. Make sure to follow coding guidelines and document changes properly.

## License
This project is licensed under the **MIT License**.

---
**Author**: Your Name  
**Project**: V.I.S.A.G.E  
**Contact**: your.email@example.com

