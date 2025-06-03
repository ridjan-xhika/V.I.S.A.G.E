import cv2
import numpy as np
import threading
import time
import os
from datetime import datetime
from collections import deque

class LiveCamera:
    def __init__(self, camera_index=0, width=640, height=480, fps=30):
        """
        Initialize the live camera with facial detection capabilities
        
        Args:
            camera_index (int): Camera device index (0 for default camera)
            width (int): Frame width
            height (int): Frame height  
            fps (int): Frames per second
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.current_frame = None
        self.processed_frame = None
        self.is_running = False
        self.frame_lock = threading.Lock()
        self.processing_enabled = True
        self.face_detection_enabled = True
        
        # Performance tracking
        self.frame_count = 0
        self.error_count = 0
        self.max_errors = 5
        self.fps_counter = deque(maxlen=30)
        self.last_fps_time = time.time()
        
        # Face detection setup
        self.setup_face_detection()
        
        # Frame processing thread
        self.process_thread = None
        
        print(f"🔧 Initializing Optimized LiveCamera: {width}x{height} @ {fps}fps")
        
        # Initialize camera
        if self.initialize_camera():
            # Start capture and processing threads
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.process_thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.is_running = True
            self.capture_thread.start()
            self.process_thread.start()
            print(f"✅ Optimized LiveCamera initialized successfully")
        else:
            print(f"❌ LiveCamera initialization failed")
            raise Exception("Failed to initialize camera")
    
    def setup_face_detection(self):
        """Initialize face detection models"""
        try:
            # Load Haar cascade for face detection (faster)
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            # Load DNN model for more accurate detection (optional)
            try:
                # You can download these from OpenCV's GitHub or use local paths
                self.net = cv2.dnn.readNetFromTensorflow(
                    'opencv_face_detector_uint8.pb',
                    'opencv_face_detector.pbtxt'
                )
                self.use_dnn = True
                print("✅ DNN face detection model loaded")
            except:
                self.use_dnn = False
                print("⚠️ DNN model not found, using Haar cascades only")
            
            print("✅ Face detection initialized")
            
        except Exception as e:
            print(f"⚠️ Face detection setup error: {e}")
            self.face_detection_enabled = False
    
    def initialize_camera(self):
        """Initialize the camera with optimal settings for performance"""
        try:
            print(f"🔌 Connecting to camera {self.camera_index}...")
            
            if self.cap is not None:
                self.cap.release()
                time.sleep(0.2)
            
            # Try different backends for better performance
            backends = [cv2.CAP_DSHOW, cv2.CAP_V4L2, cv2.CAP_ANY]
            
            for backend in backends:
                try:
                    self.cap = cv2.VideoCapture(self.camera_index, backend)
                    if self.cap.isOpened():
                        print(f"✅ Camera opened with backend {backend}")
                        break
                    else:
                        self.cap = None
                except Exception as e:
                    continue
            
            if self.cap is None or not self.cap.isOpened():
                return False
            
            # Optimize camera properties for performance
            properties = [
                (cv2.CAP_PROP_FRAME_WIDTH, self.width),
                (cv2.CAP_PROP_FRAME_HEIGHT, self.height),
                (cv2.CAP_PROP_FPS, self.fps),
                (cv2.CAP_PROP_BUFFERSIZE, 1),  # Minimize latency
                (cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')),  # Use MJPEG for better performance
            ]
            
            for prop, value in properties:
                try:
                    self.cap.set(prop, value)
                except:
                    pass
            
            # Test capture
            for attempt in range(3):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    print(f"✅ Camera test successful - Shape: {frame.shape}")
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                    return True
                time.sleep(0.1)
            
            return False
            
        except Exception as e:
            print(f"❌ Camera initialization error: {e}")
            return False
    
    def detect_faces_haar(self, frame):
        """Fast face detection using Haar cascades"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        return faces
    
    def detect_faces_dnn(self, frame):
        """More accurate face detection using DNN"""
        if not self.use_dnn:
            return []
        
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), [104, 117, 123])
        self.net.setInput(blob)
        detections = self.net.forward()
        
        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:  # Confidence threshold
                x1 = int(detections[0, 0, i, 3] * w)
                y1 = int(detections[0, 0, i, 4] * h)
                x2 = int(detections[0, 0, i, 5] * w)
                y2 = int(detections[0, 0, i, 6] * h)
                faces.append((x1, y1, x2-x1, y2-y1, confidence))
        
        return faces
    
    def process_frame_with_faces(self, frame):
        """Process frame with face detection and annotations"""
        if not self.face_detection_enabled:
            return frame
        
        try:
            # Use Haar cascades for real-time detection (faster)
            faces = self.detect_faces_haar(frame)
            
            # Draw rectangles around faces
            for (x, y, w, h) in faces:
                # Draw face rectangle
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Add face label
                cv2.putText(frame, 'Face', (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Optional: Add confidence or other info
                face_center = (x + w//2, y + h//2)
                cv2.circle(frame, face_center, 3, (0, 255, 0), -1)
            
            # Add face count
            if len(faces) > 0:
                cv2.putText(frame, f'Faces: {len(faces)}', (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            return frame
            
        except Exception as e:
            print(f"⚠️ Face processing error: {e}")
            return frame
    
    def _processing_loop(self):
        """Separate thread for frame processing to avoid blocking capture"""
        print("🎨 Frame processing loop started")
        
        while self.is_running:
            try:
                if self.current_frame is not None and self.processing_enabled:
                    with self.frame_lock:
                        frame_to_process = self.current_frame.copy()
                    
                    # Process frame with face detection
                    processed = self.process_frame_with_faces(frame_to_process)
                    
                    with self.frame_lock:
                        self.processed_frame = processed
                else:
                    time.sleep(0.01)  # Small delay when no frame to process
                    
            except Exception as e:
                print(f"❌ Processing loop error: {e}")
                time.sleep(0.1)
        
        print("🛑 Frame processing loop stopped")
    
    def _capture_loop(self):
        """Optimized capture loop with better performance"""
        print("🎬 Optimized capture loop started")
        
        target_interval = 1.0 / self.fps
        last_capture = 0
        
        while self.is_running:
            try:
                current_time = time.time()
                
                # Frame rate control
                if current_time - last_capture < target_interval:
                    time.sleep(0.001)  # Very small sleep to prevent CPU spinning
                    continue
                
                if self.cap is None or not self.cap.isOpened():
                    if not self.reconnect_camera():
                        time.sleep(1)
                        continue
                
                # Capture frame
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    with self.frame_lock:
                        self.current_frame = frame
                    
                    last_capture = current_time
                    self.frame_count += 1
                    self.error_count = 0
                    
                    # Update FPS counter
                    self.fps_counter.append(current_time)
                    
                    # Log performance occasionally
                    if self.frame_count % (self.fps * 30) == 0:  # Every 30 seconds
                        actual_fps = self.get_actual_fps()
                        print(f"📊 Frames: {self.frame_count}, FPS: {actual_fps:.1f}")
                else:
                    self.error_count += 1
                    if self.error_count >= self.max_errors:
                        print("❌ Too many capture errors, reconnecting...")
                        if not self.reconnect_camera():
                            time.sleep(2)
                    
            except Exception as e:
                self.error_count += 1
                print(f"❌ Capture error: {e}")
                if self.error_count >= self.max_errors:
                    if not self.reconnect_camera():
                        time.sleep(2)
        
        print("🛑 Capture loop stopped")
    
    def get_actual_fps(self):
        """Calculate actual FPS"""
        if len(self.fps_counter) < 2:
            return 0
        
        time_span = self.fps_counter[-1] - self.fps_counter[0]
        if time_span > 0:
            return (len(self.fps_counter) - 1) / time_span
        return 0
    
    def get_current_frame(self, processed=True):
        """Return the latest frame (processed or raw)"""
        with self.frame_lock:
            if processed and self.processed_frame is not None:
                return self.processed_frame.copy()
            elif self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    def toggle_face_detection(self):
        """Toggle face detection on/off"""
        self.face_detection_enabled = not self.face_detection_enabled
        status = "enabled" if self.face_detection_enabled else "disabled"
        print(f"👤 Face detection {status}")
        return self.face_detection_enabled
    
    def toggle_processing(self):
        """Toggle frame processing on/off for performance"""
        self.processing_enabled = not self.processing_enabled
        status = "enabled" if self.processing_enabled else "disabled"
        print(f"🎨 Frame processing {status}")
        return self.processing_enabled
    
    def reconnect_camera(self):
        """Optimized camera reconnection"""
        print("🔄 Reconnecting camera...")
        try:
            if self.cap is not None:
                self.cap.release()
                time.sleep(0.5)
            
            return self.initialize_camera()
        except Exception as e:
            print(f"❌ Reconnection error: {e}")
            return False
    
    def get_stats(self):
        """Get comprehensive camera statistics"""
        actual_fps = self.get_actual_fps()
        return {
            'frame_count': self.frame_count,
            'error_count': self.error_count,
            'actual_fps': actual_fps,
            'target_fps': self.fps,
            'is_running': self.is_running,
            'camera_open': self.cap is not None and self.cap.isOpened() if self.cap else False,
            'has_current_frame': self.current_frame is not None,
            'has_processed_frame': self.processed_frame is not None,
            'face_detection_enabled': self.face_detection_enabled,
            'processing_enabled': self.processing_enabled,
            'use_dnn': getattr(self, 'use_dnn', False)
        }
    
    def record_clip(self, duration=5.0, fps=None, with_faces=True):
        """Record a video clip with optional face detection"""
        if fps is None:
            fps = min(self.fps, 30)  # Limit recording FPS for file size
        
        try:
            filename = f'clip_{int(time.time())}.mp4'
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # Get frame dimensions
            test_frame = self.get_current_frame(processed=False)
            if test_frame is None:
                return None
            
            h, w = test_frame.shape[:2]
            out = cv2.VideoWriter(filename, fourcc, fps, (w, h))
            
            start_time = time.time()
            frame_interval = 1.0 / fps
            last_frame_time = 0
            
            print(f"🎬 Recording {duration}s clip with face detection: {with_faces}")
            
            while time.time() - start_time < duration:
                current_time = time.time()
                
                # Control recording frame rate
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.01)
                    continue
                
                frame = self.get_current_frame(processed=with_faces)
                if frame is not None:
                    out.write(frame)
                    last_frame_time = current_time
            
            out.release()
            print(f"✅ Clip recorded: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None
    
    def stop(self):
        """Stop the camera with proper cleanup"""
        print("🛑 Stopping optimized camera...")
        self.is_running = False
        
        # Wait for threads to finish
        if hasattr(self, 'capture_thread') and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)
        
        if hasattr(self, 'process_thread') and self.process_thread and self.process_thread.is_alive():
            self.process_thread.join(timeout=2)
        
        if self.cap and self.cap.isOpened():
            self.cap.release()
        
        print("✅ Optimized camera stopped")
    
    def __del__(self):
        """Clean up resources"""
        self.stop()

def take_snapshot(with_faces=True):
    """Standalone function to take a quick snapshot with face detection"""
    print("📸 Taking snapshot with face detection...")
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        
        # Quick setup for snapshot
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        time.sleep(0.5)  # Camera warm-up
        
        # Try multiple captures
        for i in range(3):
            ret, frame = cap.read()
            if ret and frame is not None:
                cap.release()
                
                # Add face detection if requested
                if with_faces:
                    try:
                        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                        face_cascade = cv2.CascadeClassifier(cascade_path)
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
                        
                        for (x, y, w, h) in faces:
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            cv2.putText(frame, 'Face', (x, y-10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                        if len(faces) > 0:
                            cv2.putText(frame, f'Faces: {len(faces)}', (10, 30), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    except Exception as e:
                        print(f"⚠️ Face detection in snapshot failed: {e}")
                
                print("✅ Snapshot with face detection captured")
                return frame
            time.sleep(0.1)
        
        cap.release()
        return None
        
    except Exception as e:
        print(f"❌ Snapshot error: {e}")
        return None