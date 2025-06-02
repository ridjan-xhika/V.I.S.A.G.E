import cv2
import numpy as np
import threading
import time
import os
from datetime import datetime

class LiveCamera:
    def __init__(self, camera_index=0, width=640, height=480, fps=30):
        """
        Initialize the live camera with specified parameters
        
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
        self.is_running = False
        self.frame_lock = threading.Lock()
        
        # Initialize camera
        self.initialize_camera()
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.is_running = True
        self.capture_thread.start()
        
        print(f"📷 LiveCamera initialized: {width}x{height} @ {fps}fps")
    
    def initialize_camera(self):
        """Initialize the camera with optimal settings"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            
            if not self.cap.isOpened():
                raise Exception(f"Cannot open camera {self.camera_index}")
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Additional optimizations
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize latency
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)   # Enable autofocus if available
            
            # Test capture
            ret, frame = self.cap.read()
            if not ret:
                raise Exception("Cannot read from camera")
            
            with self.frame_lock:
                self.current_frame = frame.copy()
                
            print("✅ Camera initialized successfully")
            
        except Exception as e:
            print(f"❌ Camera initialization failed: {e}")
            if self.cap:
                self.cap.release()
            self.cap = None
            raise
    
    def get_current_frame(self):
        """Return the latest captured frame"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    def reconnect_camera(self):
        """Attempt to reconnect to the camera"""
        print("Attempting to reconnect camera...")
        try:
            if self.cap is not None:
                self.cap.release()
            self.initialize_camera()
            print("✅ Camera reconnected successfully")
            return True
        except Exception as e:
            print(f"❌ Camera reconnection failed: {e}")
            return False
    
    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        print("🎬 Camera capture loop started")
        
        frame_time = 1.0 / self.fps
        last_capture = 0
        
        while self.is_running:
            try:
                current_time = time.time()
                
                # Control frame rate
                if current_time - last_capture < frame_time:
                    time.sleep(0.001)  # Small sleep to prevent busy waiting
                    continue
                
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    
                    if ret:
                        with self.frame_lock:
                            self.current_frame = frame.copy()
                        last_capture = current_time
                    else:
                        print("⚠️  Failed to capture frame, attempting to reconnect...")
                        self.reconnect_camera()
                else:
                    print("⚠️  Camera not available, attempting to reconnect...")
                    self.reconnect_camera()
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ Capture loop error: {e}")
                time.sleep(1)
        
        print("🛑 Camera capture loop stopped")
    
    def __del__(self):
        """Clean up resources when object is destroyed"""
        self.is_running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()