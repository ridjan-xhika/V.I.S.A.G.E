import cv2
import numpy as np
import threading
import time
import os
from datetime import datetime

class LiveCamera:
    def __init__(self, camera_index=0, width=640, height=480, fps=15):
        """
        Initialize the live camera with specified parameters
        
        Args:
            camera_index (int): Camera device index (0 for default camera)
            width (int): Frame width
            height (int): Frame height  
            fps (int): Frames per second (reduced for stability)
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.current_frame = None
        self.is_running = False
        self.frame_lock = threading.Lock()
        self.last_frame_time = 0
        self.frame_count = 0
        self.error_count = 0
        self.max_errors = 10
        
        print(f"🔧 Initializing LiveCamera: {width}x{height} @ {fps}fps")
        
        # Initialize camera
        if self.initialize_camera():
            # Start capture thread
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.is_running = True
            self.capture_thread.start()
            print(f"✅ LiveCamera initialized successfully")
        else:
            print(f"❌ LiveCamera initialization failed")
            raise Exception("Failed to initialize camera")
    
    def initialize_camera(self):
        """Initialize the camera with optimal settings"""
        try:
            print(f"🔌 Attempting to connect to camera {self.camera_index}...")
            
            # Release any existing camera connection
            if self.cap is not None:
                self.cap.release()
                time.sleep(0.5)
            
            # Try different backends for better compatibility
            backends = [cv2.CAP_DSHOW, cv2.CAP_V4L2, cv2.CAP_ANY]
            
            for backend in backends:
                try:
                    print(f"🔍 Trying backend: {backend}")
                    self.cap = cv2.VideoCapture(self.camera_index, backend)
                    
                    if self.cap.isOpened():
                        print(f"✅ Camera opened with backend {backend}")
                        break
                    else:
                        self.cap = None
                        
                except Exception as e:
                    print(f"⚠️ Backend {backend} failed: {e}")
                    continue
            
            if self.cap is None or not self.cap.isOpened():
                print("❌ All backends failed")
                return False
            
            # Set camera properties with error handling
            properties = [
                (cv2.CAP_PROP_FRAME_WIDTH, self.width),
                (cv2.CAP_PROP_FRAME_HEIGHT, self.height),
                (cv2.CAP_PROP_FPS, self.fps),
                (cv2.CAP_PROP_BUFFERSIZE, 1),  # Minimize buffer for low latency
            ]
            
            for prop, value in properties:
                try:
                    self.cap.set(prop, value)
                except Exception as e:
                    print(f"⚠️ Could not set property {prop}: {e}")
            
            # Verify camera is working by capturing a test frame
            print("🧪 Testing camera capture...")
            for attempt in range(5):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    print(f"✅ Test capture successful - Frame shape: {frame.shape}")
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                    self.error_count = 0
                    return True
                else:
                    print(f"⚠️ Test capture attempt {attempt + 1} failed")
                    time.sleep(0.2)
            
            print("❌ Camera test captures failed")
            self.cap.release()
            self.cap = None
            return False
            
        except Exception as e:
            print(f"❌ Camera initialization error: {e}")
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            return False
    
    def get_current_frame(self):
        """Return the latest captured frame"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    def reconnect_camera(self):
        """Attempt to reconnect to the camera"""
        print("🔄 Attempting to reconnect camera...")
        try:
            if self.cap is not None:
                self.cap.release()
                time.sleep(1)  # Give camera time to reset
            
            if self.initialize_camera():
                print("✅ Camera reconnected successfully")
                self.error_count = 0
                return True
            else:
                print("❌ Camera reconnection failed")
                return False
                
        except Exception as e:
            print(f"❌ Camera reconnection error: {e}")
            return False
    
    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        print("🎬 Camera capture loop started")
        
        frame_interval = 1.0 / self.fps
        last_capture_time = 0
        
        while self.is_running:
            try:
                current_time = time.time()
                
                # Control frame rate
                time_since_last = current_time - last_capture_time
                if time_since_last < frame_interval:
                    sleep_time = frame_interval - time_since_last
                    time.sleep(sleep_time)
                    continue
                
                # Check if camera is available
                if self.cap is None or not self.cap.isOpened():
                    print("⚠️ Camera not available, attempting reconnection...")
                    if not self.reconnect_camera():
                        time.sleep(2)
                        continue
                
                # Capture frame
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    # Successful capture
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                    
                    last_capture_time = current_time
                    self.frame_count += 1
                    self.error_count = 0
                    
                    # Log progress occasionally
                    if self.frame_count % (self.fps * 10) == 0:  # Every 10 seconds
                        print(f"📊 Captured {self.frame_count} frames")
                        
                else:
                    # Failed capture
                    self.error_count += 1
                    print(f"⚠️ Frame capture failed (error {self.error_count}/{self.max_errors})")
                    
                    if self.error_count >= self.max_errors:
                        print("❌ Too many capture errors, attempting reconnection...")
                        if not self.reconnect_camera():
                            print("😴 Sleeping before next reconnection attempt...")
                            time.sleep(5)
                        continue
                    
                    time.sleep(0.1)
                    
            except Exception as e:
                self.error_count += 1
                print(f"❌ Capture loop error: {e} (error {self.error_count}/{self.max_errors})")
                
                if self.error_count >= self.max_errors:
                    print("🔄 Too many errors, attempting full reconnection...")
                    if not self.reconnect_camera():
                        time.sleep(5)
                else:
                    time.sleep(0.5)
        
        print("🛑 Camera capture loop stopped")
    
    def get_stats(self):
        """Get camera statistics"""
        return {
            'frame_count': self.frame_count,
            'error_count': self.error_count,
            'is_running': self.is_running,
            'camera_open': self.cap is not None and self.cap.isOpened() if self.cap else False,
            'has_current_frame': self.current_frame is not None
        }
    
    def stop(self):
        """Stop the camera capture"""
        print("🛑 Stopping camera...")
        self.is_running = False
        
        if hasattr(self, 'capture_thread') and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)
        
        if self.cap and self.cap.isOpened():
            self.cap.release()
        
        print("✅ Camera stopped")
    
    def __del__(self):
        """Clean up resources when object is destroyed"""
        self.stop()

def take_snapshot():
    """Standalone function to take a quick snapshot"""
    print("📸 Taking standalone snapshot...")
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera for snapshot")
            return None
        
        # Let camera warm up
        time.sleep(0.5)
        
        # Try multiple captures to get a good frame
        for i in range(5):
            ret, frame = cap.read()
            if ret and frame is not None:
                cap.release()
                print(f"✅ Snapshot captured successfully")
                return frame
            time.sleep(0.1)
        
        cap.release()
        print("❌ Snapshot capture failed")
        return None
        
    except Exception as e:
        print(f"❌ Snapshot error: {e}")
        return None