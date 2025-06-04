import sys
import os
import time
import threading
import socket
import cv2
import json
from flask import Flask, Response, render_template_string, jsonify
from pyngrok import ngrok
from datetime import datetime

from src import bot, camera

# Flask app for video streaming
flask_app = Flask(__name__)

# Global variables
streaming_active = False
camera_instance = None
face_detection_enabled = False
face_detection_data = {
    'total_faces': 0,
    'last_detection': None,
    'current_faces': 0,
    'alert_active': False
}

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

def detect_faces_in_frame(frame):
    """Detect faces in a frame using OpenCV Haar Cascades"""
    global face_detection_data
    
    if not face_detection_enabled or frame is None:
        return frame, []
    
    try:
        # Convert frame to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Load Haar cascade for face detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # Update detection data
        current_face_count = len(faces)
        face_detection_data['current_faces'] = current_face_count
        
        if current_face_count > 0:
            face_detection_data['total_faces'] += current_face_count
            face_detection_data['last_detection'] = datetime.now().isoformat()
            face_detection_data['alert_active'] = True
            
            print(f"👤 {current_face_count} face(s) detected!")
            
            # Draw rectangles around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, 'FACE DETECTED', (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            face_detection_data['alert_active'] = False
        
        return frame, faces
        
    except Exception as e:
        print(f"❌ Face detection error: {e}")
        return frame, []

def generate_frames():
    """Generate frames for the video stream using the active camera"""
    global streaming_active, camera_instance
    
    print("🎬 Starting frame generation...")
    
    while streaming_active:
        try:
            frame = None
            
            # Try to get frame from camera instance
            if camera_instance and hasattr(camera_instance, 'get_current_frame'):
                frame = camera_instance.get_current_frame()
            
            # Fallback to direct camera access if no frame
            if frame is None:
                try:
                    cap = cv2.VideoCapture(0)
                    if cap.isOpened():
                        # Wait a moment for camera to initialize
                        time.sleep(0.1)
                        ret, frame = cap.read()
                        cap.release()
                        if not ret or frame is None:
                            frame = None
                    else:
                        cap.release()
                except Exception as e:
                    print(f"❌ Fallback camera error: {e}")
                    frame = None
            
            # If we have a frame, process it for face detection
            if frame is not None:
                try:
                    # Apply face detection if enabled
                    processed_frame, detected_faces = detect_faces_in_frame(frame)
                    
                    # Encode frame as JPEG
                    success, buffer = cv2.imencode('.jpg', processed_frame, [
                        cv2.IMWRITE_JPEG_QUALITY, 85,
                        cv2.IMWRITE_JPEG_OPTIMIZE, 1
                    ])
                    
                    if success:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    else:
                        print("❌ Frame encoding failed")
                        
                except Exception as e:
                    print(f"❌ Frame processing error: {e}")
            else:
                # Send a placeholder frame when no camera is available
                placeholder = create_placeholder_frame()
                success, buffer = cv2.imencode('.jpg', placeholder)
                if success:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
            # Control frame rate
            time.sleep(0.033)  # ~30 FPS
            
        except Exception as e:
            print(f"❌ Frame generation error: {e}")
            time.sleep(0.1)
    
    print("🛑 Frame generation stopped")

def create_placeholder_frame():
    """Create a placeholder frame when camera is not available"""
    placeholder = cv2.imread('placeholder.jpg') if os.path.exists('placeholder.jpg') else None
    
    if placeholder is None:
        # Create a simple placeholder
        placeholder = cv2.zeros((480, 640, 3), dtype=cv2.uint8)
        cv2.putText(placeholder, 'Camera Not Available', (160, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    return placeholder

@flask_app.route('/')
def index():
    """Video streaming home page with face detection alerts"""
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
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
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
            background: #f0f0f0;
            position: relative;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .video-stream {
            width: 100%;
            height: auto;
            display: block;
            max-width: 100%;
        }
        .loading-message {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #666;
            font-size: 18px;
        }
        .controls {
            margin-top: 20px;
        }
        .btn {
            margin: 5px;
            padding: 10px 20px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        .refresh-btn {
            background: #ee5a24;
            color: white;
        }
        .refresh-btn:hover {
            background: #d63a04;
        }
        .status-btn {
            background: #2ecc71;
            color: white;
        }
        .status-btn:hover {
            background: #27ae60;
        }
        .face-toggle-btn {
            background: #3742fa;
            color: white;
        }
        .face-toggle-btn:hover {
            background: #2f3542;
        }
        .face-toggle-btn.active {
            background: #ff6b6b;
        }
        .status-info {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            font-size: 14px;
            color: #666;
        }
        .alert-banner {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #ff4757;
            color: white;
            padding: 15px 30px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 16px;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s ease;
            box-shadow: 0 4px 15px rgba(255, 71, 87, 0.4);
        }
        .alert-banner.show {
            opacity: 1;
        }
        .face-detection-status {
            margin-top: 10px;
            padding: 10px;
            background: #e8f4f8;
            border-radius: 8px;
            font-size: 12px;
            color: #2c3e50;
        }
        .face-count {
            font-weight: bold;
            color: #e74c3c;
        }
        .detection-active {
            background: #ffecec !important;
            border: 2px solid #ff4757;
        }
    </style>
</head>
<body>
    <div id="alertBanner" class="alert-banner">
        🚨 FACE DETECTED! 🚨
    </div>
    
    <div class="container">
        <h1>🎥 V.I.S.A.G.E Live Stream</h1>
        <div class="video-container" id="videoContainer">
            <img id="videoStream" class="video-stream" src="{{ url_for('video_feed') }}" 
                 alt="Live Stream" style="display: none;">
            <div id="loadingMessage" class="loading-message">🔄 Loading camera feed...</div>
        </div>
        <div class="controls">
            <button class="btn refresh-btn" onclick="refreshStream()">🔄 Refresh Stream</button>
            <button class="btn status-btn" onclick="checkStatus()">📊 Check Status</button>
            <button id="faceToggleBtn" class="btn face-toggle-btn" onclick="toggleFaceDetection()">
                👤 Enable Face Detection
            </button>
        </div>
        <div class="face-detection-status">
            <div>Face Detection: <span id="faceDetectionStatus">Disabled</span></div>
            <div>Current Faces: <span id="currentFaceCount" class="face-count">0</span></div>
            <div>Total Detected: <span id="totalFaceCount" class="face-count">0</span></div>
            <div>Last Detection: <span id="lastDetection">Never</span></div>
        </div>
        <div id="statusInfo" class="status-info" style="display: none;">
            <div id="statusText">Checking status...</div>
        </div>
    </div>

    <script>
        const videoStream = document.getElementById('videoStream');
        const videoContainer = document.getElementById('videoContainer');
        const loadingMessage = document.getElementById('loadingMessage');
        const statusInfo = document.getElementById('statusInfo');
        const statusText = document.getElementById('statusText');
        const alertBanner = document.getElementById('alertBanner');
        const faceToggleBtn = document.getElementById('faceToggleBtn');
        const faceDetectionStatus = document.getElementById('faceDetectionStatus');
        const currentFaceCount = document.getElementById('currentFaceCount');
        const totalFaceCount = document.getElementById('totalFaceCount');
        const lastDetection = document.getElementById('lastDetection');
        
        let streamLoaded = false;
        let retryCount = 0;
        const maxRetries = 5;
        let faceDetectionEnabled = false;
        let statusUpdateInterval = null;
        let alertActive = false;
        
        function showAlert() {
            if (!alertActive) {
                alertActive = true;
                alertBanner.classList.add('show');
                videoContainer.classList.add('detection-active');
                
                // Play alert sound
                try {
                    const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwUGNx');
                    audio.volume = 0.3;
                    audio.play().catch(() => {});
                } catch (e) {}
                
                setTimeout(() => {
                    alertBanner.classList.remove('show');
                    videoContainer.classList.remove('detection-active');
                    alertActive = false;
                }, 3000);
            }
        }
        
        function hideAlert() {
            alertBanner.classList.remove('show');
            videoContainer.classList.remove('detection-active');
            alertActive = false;
        }
        
        function updateFaceDetectionStatus() {
            if (!faceDetectionEnabled) return;
            
            fetch('/api/face_detection')
                .then(response => response.json())
                .then(data => {
                    currentFaceCount.textContent = data.current_faces;
                    totalFaceCount.textContent = data.total_faces;
                    
                    if (data.last_detection) {
                        const date = new Date(data.last_detection);
                        lastDetection.textContent = date.toLocaleTimeString();
                    }
                    
                    // Show/hide alert based on detection
                    if (data.alert_active && data.current_faces > 0) {
                        showAlert();
                    } else if (!data.alert_active) {
                        hideAlert();
                    }
                })
                .catch(error => {
                    console.error('Face detection status error:', error);
                });
        }
        
        async function toggleFaceDetection() {
            try {
                const response = await fetch('/api/toggle_face_detection', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const data = await response.json();
                faceDetectionEnabled = data.enabled;
                
                if (faceDetectionEnabled) {
                    faceToggleBtn.textContent = '🛑 Disable Face Detection';
                    faceToggleBtn.classList.add('active');
                    faceDetectionStatus.textContent = 'Enabled';
                    
                    // Start status updates
                    statusUpdateInterval = setInterval(updateFaceDetectionStatus, 1000);
                    console.log('👤 Face detection enabled');
                } else {
                    faceToggleBtn.textContent = '👤 Enable Face Detection';
                    faceToggleBtn.classList.remove('active');
                    faceDetectionStatus.textContent = 'Disabled';
                    
                    // Stop status updates
                    if (statusUpdateInterval) {
                        clearInterval(statusUpdateInterval);
                        statusUpdateInterval = null;
                    }
                    
                    // Clear detection data
                    currentFaceCount.textContent = '0';
                    hideAlert();
                    console.log('🛑 Face detection disabled');
                }
            } catch (error) {
                console.error('Toggle face detection error:', error);
                alert('Failed to toggle face detection');
            }
        }
        
        function showVideo() {
            videoStream.style.display = 'block';
            loadingMessage.style.display = 'none';
            streamLoaded = true;
            console.log('✅ Video stream loaded successfully');
        }
        
        function showLoading() {
            videoStream.style.display = 'none';
            loadingMessage.style.display = 'block';
            loadingMessage.textContent = '🔄 Loading camera feed...';
            streamLoaded = false;
        }
        
        function showError(message) {
            videoStream.style.display = 'none';
            loadingMessage.style.display = 'block';
            loadingMessage.textContent = message || '❌ Camera feed unavailable';
            streamLoaded = false;
        }
        
        function refreshStream() {
            console.log('🔄 Refreshing stream...');
            showLoading();
            retryCount = 0;
            
            const timestamp = new Date().getTime();
            const newSrc = '{{ url_for("video_feed") }}?t=' + timestamp;
            
            videoStream.src = '';
            setTimeout(() => {
                videoStream.src = newSrc;
            }, 100);
        }
        
        function checkStatus() {
            statusInfo.style.display = 'block';
            statusText.textContent = 'Checking status...';
            
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    const status = data.streaming ? '✅ Active' : '❌ Inactive';
                    const camera = data.camera ? '✅ Connected' : '❌ Disconnected';
                    const faceDetection = data.face_detection ? '✅ Active' : '❌ Inactive';
                    statusText.innerHTML = `
                        <strong>Stream Status:</strong> ${status}<br>
                        <strong>Camera:</strong> ${camera}<br>
                        <strong>Face Detection:</strong> ${faceDetection}<br>
                        <strong>Last Update:</strong> ${new Date(data.timestamp * 1000).toLocaleTimeString()}
                    `;
                })
                .catch(error => {
                    statusText.textContent = '❌ Failed to check status';
                    console.error('Status check error:', error);
                });
        }
        
        // Event listeners for video stream
        videoStream.onload = showVideo;
        videoStream.onloadstart = () => console.log('🔄 Stream loading started...');
        videoStream.onerror = function() {
            console.error('❌ Video stream error');
            retryCount++;
            
            if (retryCount < maxRetries) {
                console.log(`🔄 Retrying... (${retryCount}/${maxRetries})`);
                setTimeout(() => {
                    const timestamp = new Date().getTime();
                    videoStream.src = '{{ url_for("video_feed") }}?retry=' + retryCount + '&t=' + timestamp;
                }, 2000);
            } else {
                showError('❌ Camera feed unavailable after multiple retries');
            }
        };
        
        // Auto-refresh every 30 seconds if stream is not loaded
        setInterval(() => {
            if (!streamLoaded) {
                console.log('🔄 Auto-refreshing due to no stream...');
                refreshStream();
            }
        }, 30000);
        
        // Initialize on page load
        window.addEventListener('load', () => {
            setTimeout(checkStatus, 1000);
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (statusUpdateInterval) {
                clearInterval(statusUpdateInterval);
            }
        });
    </script>
</body>
</html>
''')

@flask_app.route('/video_feed')
def video_feed():
    """MJPEG video stream"""
    print("📹 Video feed requested")
    
    if not streaming_active:
        print("⚠️ Streaming not active")
        # Return a simple response indicating stream is not active
        def empty_stream():
            yield b'--frame\r\n'
            yield b'Content-Type: text/plain\r\n\r\n'
            yield b'Stream not active\r\n'
        return Response(empty_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    return Response(generate_frames(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame',
                   headers={
                       'Cache-Control': 'no-cache, no-store, must-revalidate',
                       'Pragma': 'no-cache',
                       'Expires': '0'
                   })

@flask_app.route('/api/status')
def api_status():
    """API endpoint for camera/stream status"""
    return {
        'streaming': streaming_active,
        'camera': camera_instance is not None,
        'face_detection': face_detection_enabled,
        'timestamp': time.time(),
        'camera_active': camera_instance is not None and hasattr(camera_instance, 'is_running') and camera_instance.is_running if camera_instance else False
    }

@flask_app.route('/api/face_detection')
def api_face_detection():
    """API endpoint for face detection data"""
    return jsonify(face_detection_data)

@flask_app.route('/api/toggle_face_detection', methods=['POST'])
def api_toggle_face_detection():
    """API endpoint to toggle face detection"""
    global face_detection_enabled, face_detection_data
    
    face_detection_enabled = not face_detection_enabled
    
    if not face_detection_enabled:
        # Reset detection data when disabled
        face_detection_data = {
            'total_faces': 0,
            'last_detection': None,
            'current_faces': 0,
            'alert_active': False
        }
    
    print(f"👤 Face detection {'enabled' if face_detection_enabled else 'disabled'}")
    
    return jsonify({
        'enabled': face_detection_enabled,
        'message': f"Face detection {'enabled' if face_detection_enabled else 'disabled'}"
    })

def start_flask_server():
    """Run Flask app and expose via ngrok"""
    try:
        print("🌐 Starting Flask server...")
        # Set ngrok auth token if needed (you may need to set this)
        # ngrok.set_auth_token("your_token_here")
        
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

def enable_face_detection():
    """Enable face detection from bot commands"""
    global face_detection_enabled
    face_detection_enabled = True
    print("👤 Face detection enabled via bot command")

def disable_face_detection():
    """Disable face detection from bot commands"""
    global face_detection_enabled, face_detection_data
    face_detection_enabled = False
    face_detection_data = {
        'total_faces': 0,
        'last_detection': None,
        'current_faces': 0,
        'alert_active': False
    }
    print("🛑 Face detection disabled via bot command")

def get_face_detection_status():
    """Get current face detection status and data"""
    return {
        'enabled': face_detection_enabled,
        'data': face_detection_data
    }

def set_camera_instance(cam_instance):
    """Store camera instance globally"""
    global camera_instance
    camera_instance = cam_instance
    print(f"📷 Camera instance set: {cam_instance is not None}")

def test_camera_direct():
    """Test direct camera access"""
    print("🧪 Testing direct camera access...")
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera device 0")
            return False
        
        ret, frame = cap.read()
        cap.release()
        
        if ret and frame is not None:
            print(f"✅ Direct camera test successful - Frame shape: {frame.shape}")
            return True
        else:
            print("❌ Direct camera test failed - No frame captured")
            return False
    except Exception as e:
        print(f"❌ Direct camera test error: {e}")
        return False

def main():
    print("🚀 Starting V.I.S.A.G.E System...")
    print("=" * 50)
    
    # Test camera first
    if not test_camera_direct():
        print("⚠️ Camera test failed, but continuing...")
    
    # Start Flask server
    flask_thread = threading.Thread(target=start_flask_server, daemon=True)
    flask_thread.start()
    print("🌐 Flask server starting on port 5000...")
    
    # Initialize camera
    try:
        print("📷 Initializing camera...")
        cam = camera.LiveCamera()
        set_camera_instance(cam)
        print("📷 Camera initialized and assigned...")
        
        # Start streaming by default
        start_streaming()
        
    except Exception as e:
        print(f"⚠️ Camera initialization error: {e}")
        print("🔄 Attempting to continue without camera instance...")
        # Start streaming anyway - it will use fallback
        start_streaming()
    
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
    print("   • /enable_face_detection")
    print("   • /disable_face_detection")
    print("   • /face_status")
    print("=" * 50)
    
    try:
        bot.run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down V.I.S.A.G.E...")
        stop_streaming()
    except Exception as e:
        print(f"❌ Bot error: {e}")

# Exported for bot
__all__ = [
    'start_streaming', 
    'stop_streaming', 
    'get_local_ip', 
    'streaming_active', 
    'set_camera_instance',
    'enable_face_detection',
    'disable_face_detection',
    'get_face_detection_status'
]

if __name__ == "__main__":
    main()