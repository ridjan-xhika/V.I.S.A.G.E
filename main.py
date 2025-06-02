import sys
import os
import time
import threading
import socket
import cv2
from flask import Flask, Response, render_template_string
from pyngrok import ngrok

from src import bot, camera

# Flask app for video streaming
flask_app = Flask(__name__)

# Global variables
streaming_active = False
camera_instance = None

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def generate_frames():
    """Generate frames for the video stream using the active camera"""
    global streaming_active, camera_instance
    while streaming_active:
        try:
            frame = None

            if camera_instance and hasattr(camera_instance, 'get_current_frame'):
                frame = camera_instance.get_current_frame()
                if frame is None:
                    print("⚠️ Camera returned no frame")
            elif hasattr(camera, 'take_snapshot'):
                print("⚠️ Fallback to camera.take_snapshot()")
                frame = camera.take_snapshot()
            else:
                print("⚠️ Fallback to temporary camera")
                cap = cv2.VideoCapture(0)
                time.sleep(0.5)
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    print("❌ Fallback capture failed")
                    frame = None

            if frame is not None:
                success, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if success:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
                else:
                    print("❌ Frame encoding failed")
            else:
                print("⚠️ Empty frame, retrying...")
                time.sleep(0.1)

        except Exception as e:
            print(f"❌ Streaming error: {e}")
            time.sleep(0.2)

@flask_app.route('/')
def index():
    """Video streaming home page"""
    return render_template_string('''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>V.I.S.A.G.E Live Stream</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            width: 100%;
            max-width: 900px;
            background: white;
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            text-align: center;
        }
        .video-container {
            margin: 30px 0;
            border-radius: 15px;
            overflow: hidden;
        }
        img {
            width: 100%;
            display: block;
        }
        .refresh-btn {
            margin-top: 20px;
            padding: 10px 20px;
            background: #ee5a24;
            color: white;
            border: none;
            border-radius: 20px;
            cursor: pointer;
        }
    </style>
    <script>
        function refreshStream() {
            const img = document.querySelector('img');
            const src = img.src;
            img.src = '';
            setTimeout(() => { img.src = src; }, 100);
        }
        setInterval(refreshStream, 30000);
    </script>
</head>
<body>
    <div class="container">
        <h1>🎥 V.I.S.A.G.E Live Stream</h1>
        <div class="video-container">
            <img src="{{ url_for('video_feed') }}" alt="Live Stream" onerror="this.style.display='none'">
        </div>
        <button class="refresh-btn" onclick="refreshStream()">🔄 Refresh Stream</button>
    </div>
</body>
</html>
''')

@flask_app.route('/video_feed')
def video_feed():
    """MJPEG video stream"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@flask_app.route('/api/status')
def api_status():
    """API endpoint for camera/stream status"""
    return {
        'streaming': streaming_active,
        'camera': camera_instance is not None,
        'timestamp': time.time()
    }

def start_flask_server():
    """Run Flask app and expose via ngrok"""
    try:
        public_url = ngrok.connect(5000)
        print(f"🌍 Public URL: {public_url}")
        flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"❌ Flask error: {e}")

def start_streaming():
    """Enable streaming"""
    global streaming_active
    streaming_active = True
    print(f"🎥 Live stream started at http://{get_local_ip()}:5000")

def stop_streaming():
    """Disable streaming"""
    global streaming_active
    streaming_active = False
    print("🛑 Live stream stopped")

def set_camera_instance(cam_instance):
    """Store camera instance globally"""
    global camera_instance
    camera_instance = cam_instance

def main():
    print("🚀 Starting V.I.S.A.G.E System...")
    print("=" * 50)

    # Start Flask server
    flask_thread = threading.Thread(target=start_flask_server, daemon=True)
    flask_thread.start()
    print("🌐 Flask server starting on port 5000...")

    # Initialize camera
    try:
        cam = camera.LiveCamera()
        set_camera_instance(cam)
        print("📷 Camera initialized and assigned...")
    except Exception as e:
        print(f"⚠️ Camera error: {e}")

    # Give Flask time to start
    time.sleep(3)

    print("=" * 50)
    print("🎯 SYSTEM READY")
    print(f"🌐 Web interface: http://{get_local_ip()}:5000")
    print(f"📱 Local access: http://localhost:5000")
    print("💬 Telegram commands:")
    print("   • /start_stream")
    print("   • /live")
    print("   • /stop_stream")
    print("=" * 50)

    try:
        bot.run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down V.I.S.A.G.E...")
        stop_streaming()
    except Exception as e:
        print(f"❌ Bot error: {e}")

# Exported for bot
__all__ = ['start_streaming', 'stop_streaming', 'get_local_ip', 'streaming_active', 'set_camera_instance']

if __name__ == "__main__":
    main()
