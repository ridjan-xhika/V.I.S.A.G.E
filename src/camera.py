import cv2
import numpy as np
import threading
import time
import os
from datetime import datetime
from collections import deque
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LiveCamera:
    def __init__(self, camera_index=0, width=640, height=480, fps=30, enable_logging=True):
        """
        Initialize the live camera
        
        Args:
            camera_index (int): Camera device index (0 for default camera)
            width (int): Frame width
            height (int): Frame height  
            fps (int): Frames per second
            enable_logging (bool): Enable detailed logging
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.enable_logging = enable_logging
        
        # Camera and threading
        self.cap = None
        self.current_frame = None
        self.raw_frame = None
        self.is_running = False
        self.frame_lock = threading.Lock()
        
        # Performance tracking
        self.frame_count = 0
        self.error_count = 0
        self.max_errors = 5
        self.fps_counter = deque(maxlen=30)
        self.last_fps_time = time.time()
        self.start_time = time.time()
        
        # Threading
        self.capture_thread = None
        
        if self.enable_logging:
            logger.info(f"🔧 Initializing LiveCamera: {width}x{height} @ {fps}fps")
        
        # Initialize camera
        if self.initialize_camera():
            # Start capture thread
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.is_running = True
            self.capture_thread.start()
            
            if self.enable_logging:
                logger.info("✅ LiveCamera initialized successfully")
        else:
            if self.enable_logging:
                logger.error("❌ LiveCamera initialization failed")
            raise Exception("Failed to initialize camera")
    
    def initialize_camera(self):
        """Initialize the camera with optimal settings for performance"""
        try:
            if self.enable_logging:
                logger.info(f"🔌 Connecting to camera {self.camera_index}...")
            
            if self.cap is not None:
                self.cap.release()
                time.sleep(0.2)
            
            # Try different backends for better performance
            backends = [cv2.CAP_DSHOW, cv2.CAP_V4L2, cv2.CAP_ANY]
            
            for backend in backends:
                try:
                    self.cap = cv2.VideoCapture(self.camera_index, backend)
                    if self.cap.isOpened():
                        if self.enable_logging:
                            logger.info(f"✅ Camera opened with backend {backend}")
                        break
                    else:
                        self.cap = None
                except Exception:
                    continue
            
            if self.cap is None or not self.cap.isOpened():
                return False
            
            # Optimize camera properties for performance
            properties = [
                (cv2.CAP_PROP_FRAME_WIDTH, self.width),
                (cv2.CAP_PROP_FRAME_HEIGHT, self.height),
                (cv2.CAP_PROP_FPS, self.fps),
                (cv2.CAP_PROP_BUFFERSIZE, 1),  # Minimize latency
                (cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')),
            ]
            
            for prop, value in properties:
                try:
                    self.cap.set(prop, value)
                except Exception:
                    pass
            
            # Test capture
            for attempt in range(3):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    if self.enable_logging:
                        logger.info(f"✅ Camera test successful - Shape: {frame.shape}")
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                        self.raw_frame = frame.copy()
                    return True
                time.sleep(0.1)
            
            return False
            
        except Exception as e:
            if self.enable_logging:
                logger.error(f"❌ Camera initialization error: {e}")
            return False
    
    def _capture_loop(self):
        """Optimized capture loop with better performance"""
        if self.enable_logging:
            logger.info("🎬 Capture loop started")
        
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
                        self.current_frame = frame.copy()
                        self.raw_frame = frame.copy()
                    
                    last_capture = current_time
                    self.frame_count += 1
                    self.error_count = 0
                    
                    # Update FPS counter
                    self.fps_counter.append(current_time)
                    
                    # Log performance occasionally
                    if self.enable_logging and self.frame_count % (self.fps * 30) == 0:  # Every 30 seconds
                        actual_fps = self.get_actual_fps()
                        logger.info(f"📊 Frames: {self.frame_count}, FPS: {actual_fps:.1f}")
                else:
                    self.error_count += 1
                    if self.error_count >= self.max_errors:
                        if self.enable_logging:
                            logger.warning("❌ Too many capture errors, reconnecting...")
                        if not self.reconnect_camera():
                            time.sleep(2)
                    
            except Exception as e:
                self.error_count += 1
                if self.enable_logging:
                    logger.error(f"❌ Capture error: {e}")
                if self.error_count >= self.max_errors:
                    if not self.reconnect_camera():
                        time.sleep(2)
        
        if self.enable_logging:
            logger.info("🛑 Capture loop stopped")
    
    def get_actual_fps(self):
        """Calculate actual FPS"""
        if len(self.fps_counter) < 2:
            return 0
        
        time_span = self.fps_counter[-1] - self.fps_counter[0]
        if time_span > 0:
            return (len(self.fps_counter) - 1) / time_span
        return 0
    
    def get_current_frame(self, security_overlay=True):
        """Return the latest raw frame with optional security overlay"""
        with self.frame_lock:
            if self.current_frame is not None:
                frame = self.current_frame.copy()
                if security_overlay:
                    frame = self.add_security_overlay(frame)
                return frame
        return None
    
    def read_frame(self, security_overlay=True):
        """Return current frame with optional security overlay - For bot commands"""
        with self.frame_lock:
            if self.current_frame is not None:
                frame = self.current_frame.copy()
                if security_overlay:
                    frame = self.add_security_overlay(frame)
                return True, frame
        return False, None
    
    def read(self):
        """Standard OpenCV-style read method"""
        return self.read_frame()
    
    def reconnect_camera(self):
        """Optimized camera reconnection"""
        if self.enable_logging:
            logger.info("🔄 Reconnecting camera...")
        try:
            if self.cap is not None:
                self.cap.release()
                time.sleep(0.5)
            
            return self.initialize_camera()
        except Exception as e:
            if self.enable_logging:
                logger.error(f"❌ Reconnection error: {e}")
            return False
    
    def get_stats(self):
        """Get comprehensive camera statistics"""
        actual_fps = self.get_actual_fps()
        uptime = time.time() - self.start_time
        
        return {
            'frame_count': self.frame_count,
            'error_count': self.error_count,
            'actual_fps': actual_fps,
            'target_fps': self.fps,
            'is_running': self.is_running,
            'camera_open': self.cap is not None and self.cap.isOpened() if self.cap else False,
            'has_current_frame': self.current_frame is not None,
            'has_raw_frame': self.raw_frame is not None,
            'uptime': uptime,
            'width': self.width,
            'height': self.height
        }
    
    def record_clip(self, duration=5.0, fps=None):
        """Record a video clip"""
        if fps is None:
            fps = min(self.fps, 30)  # Limit recording FPS for file size
        
        try:
            filename = f'clip_{int(time.time())}.mp4'
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # Get frame dimensions
            test_frame = self.get_current_frame()
            if test_frame is None:
                return None
            
            h, w = test_frame.shape[:2]
            out = cv2.VideoWriter(filename, fourcc, fps, (w, h))
            
            start_time = time.time()
            frame_interval = 1.0 / fps
            last_frame_time = 0
            
            if self.enable_logging:
                logger.info(f"🎬 Recording {duration}s clip")
            
            while time.time() - start_time < duration:
                current_time = time.time()
                
                # Control recording frame rate
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.01)
                    continue
                
                frame = self.get_current_frame()
                if frame is not None:
                    out.write(frame)
                    last_frame_time = current_time
            
            out.release()
            if self.enable_logging:
                logger.info(f"✅ Clip recorded: {filename}")
            return filename
            
        except Exception as e:
            if self.enable_logging:
                logger.error(f"❌ Recording error: {e}")
            return None
    
    def add_security_overlay(self, frame):
        """Add security camera style overlay with timestamp and info"""
        h, w = frame.shape[:2]
        
        # Create semi-transparent overlay areas
        overlay = frame.copy()
        
        # Top bar for camera info
        cv2.rectangle(overlay, (0, 0), (w, 35), (0, 0, 0), -1)
        # Bottom bar for timestamp
        cv2.rectangle(overlay, (0, h-35), (w, h), (0, 0, 0), -1)
        
        # Blend overlay with original frame
        frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)
        
        # Camera identification (top left)
        camera_id = f"CAM-{self.camera_index:02d}"
        cv2.putText(frame, camera_id, (10, 20), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)
        
        # Recording indicator (top left, after camera ID)
        cv2.circle(frame, (100, 15), 5, (0, 0, 255), -1)  # Red dot
        cv2.putText(frame, "REC", (115, 20), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 255), 1)
        
        # Resolution info (top right)
        resolution = f"{w}x{h}"
        text_size = cv2.getTextSize(resolution, cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)[0]
        cv2.putText(frame, resolution, (w - text_size[0] - 10, 20), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)
        
        # Timestamp (bottom left) - Security camera style
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%H:%M:%S")
        
        cv2.putText(frame, f"{date_str} {time_str}", (10, h - 10), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)
        
        # Frame counter (bottom right)
        frame_text = f"FRAME: {self.frame_count:08d}"
        text_size = cv2.getTextSize(frame_text, cv2.FONT_HERSHEY_DUPLEX, 0.4, 1)[0]
        cv2.putText(frame, frame_text, (w - text_size[0] - 10, h - 10), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.4, (255, 255, 255), 1)
        
        # Add corner brackets for security camera look
        bracket_size = 20
        bracket_thickness = 2
        bracket_color = (0, 255, 0)
        
        # Top-left corner
        cv2.line(frame, (5, 40), (5, 40 + bracket_size), bracket_color, bracket_thickness)
        cv2.line(frame, (5, 40), (5 + bracket_size, 40), bracket_color, bracket_thickness)
        
        # Top-right corner
        cv2.line(frame, (w-5, 40), (w-5, 40 + bracket_size), bracket_color, bracket_thickness)
        cv2.line(frame, (w-5, 40), (w-5 - bracket_size, 40), bracket_color, bracket_thickness)
        
        # Bottom-left corner
        cv2.line(frame, (5, h-40), (5, h-40 - bracket_size), bracket_color, bracket_thickness)
        cv2.line(frame, (5, h-40), (5 + bracket_size, h-40), bracket_color, bracket_thickness)
        
        # Bottom-right corner
        cv2.line(frame, (w-5, h-40), (w-5, h-40 - bracket_size), bracket_color, bracket_thickness)
        cv2.line(frame, (w-5, h-40), (w-5 - bracket_size, h-40), bracket_color, bracket_thickness)
        
        return frame
    
    def is_opened(self):
        """Check if camera is opened"""
        return self.cap is not None and self.cap.isOpened() if self.cap else False
    
    def release(self):
        """Release camera resources"""
        self.stop()
    
    def stop(self):
        """Stop the camera with proper cleanup"""
        if self.enable_logging:
            logger.info("🛑 Stopping camera...")
        
        self.is_running = False
        
        # Wait for thread to finish
        if hasattr(self, 'capture_thread') and self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)
        
        if self.cap and self.cap.isOpened():
            self.cap.release()
        
        if self.enable_logging:
            logger.info("✅ Camera stopped")
    
    def __del__(self):
        """Clean up resources"""
        try:
            self.stop()
        except Exception:
            pass

def take_snapshot(security_overlay=True):
    """Standalone function to take a quick snapshot with security camera styling"""
    logger.info("📸 Taking security camera snapshot...")
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
                
                if security_overlay:
                    # Add security camera overlay
                    h, w = frame.shape[:2]
                    
                    # Create overlay areas
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (0, 0), (w, 35), (0, 0, 0), -1)
                    cv2.rectangle(overlay, (0, h-35), (w, h), (0, 0, 0), -1)
                    frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)
                    
                    # Camera info
                    cv2.putText(frame, "CAM-00", (10, 20), 
                               cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)
                    cv2.circle(frame, (100, 15), 5, (0, 0, 255), -1)
                    cv2.putText(frame, "REC", (115, 20), 
                               cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 255), 1)
                    
                    # Timestamp
                    now = datetime.now()
                    timestamp = f"{now.strftime('%d/%m/%Y')} {now.strftime('%H:%M:%S')}"
                    cv2.putText(frame, timestamp, (10, h - 10), 
                               cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)
                    
                    # Corner brackets
                    bracket_size = 20
                    bracket_color = (0, 255, 0)
                    cv2.line(frame, (5, 40), (5, 60), bracket_color, 2)
                    cv2.line(frame, (5, 40), (25, 40), bracket_color, 2)
                    cv2.line(frame, (w-5, 40), (w-5, 60), bracket_color, 2)
                    cv2.line(frame, (w-5, 40), (w-25, 40), bracket_color, 2)
                    cv2.line(frame, (5, h-40), (5, h-60), bracket_color, 2)
                    cv2.line(frame, (5, h-40), (25, h-40), bracket_color, 2)
                    cv2.line(frame, (w-5, h-40), (w-5, h-60), bracket_color, 2)
                    cv2.line(frame, (w-5, h-40), (w-25, h-40), bracket_color, 2)
                
                logger.info("✅ Security camera snapshot captured")
                return frame
            time.sleep(0.1)
        
        cap.release()
        return None
        
    except Exception as e:
        logger.error(f"❌ Snapshot error: {e}")
        return None

# Compatibility alias for existing code
Camera = LiveCamera