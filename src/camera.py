import cv2
import numpy as np
import threading
import time
from datetime import datetime
from collections import deque
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LiveCamera:
    def __init__(
        self,
        camera_index=0,
        width=2560,
        height=1400,
        fps=240,
        enable_logging=True,
        motion_check_interval=2
    ):
        """
        Initialize the live camera

        Args:
            camera_index (int): Camera device index (0 for default camera)
            width (int): Frame width (lower resolution → higher FPS)
            height (int): Frame height
            fps (int): Target frames per second
            enable_logging (bool): Enable detailed logging
            motion_check_interval (int): Only enqueue every Nth frame for detection
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.enable_logging = enable_logging
        self.motion_check_interval = max(1, motion_check_interval)

        # Camera and threading
        self.cap = None
        self.current_frame = None  # Last frame with overlay
        self.raw_frame = None      # Last raw frame (no overlay)
        self.frame_lock = threading.Lock()
        self.is_running = False

        # Motion detection
        self.motion_detection_enabled = True
        self.background_subtractor = None
        self.motion_threshold = 500    # Minimum area for motion detection
        self.motion_sensitivity = 25   # Background learning rate
        self.motion_detected = False
        self.motion_areas = []
        self.last_motion_time = 0
        self.motion_cooldown = 2.0     # Seconds between motion detections

        # Fast motion‐detection parameters
        self._motion_scale_w = 160
        self._motion_scale_h = 120
        self._fast_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

        # Statistics
        self.frame_count = 0
        self.error_count = 0
        self.max_errors = 5
        self.fps_counter = deque(maxlen=30)
        self.start_time = time.time()

        # Threading
        self.capture_thread = None
        self.detection_thread = None
        self.detection_running = False
        self._internal_frame_counter = 0

        if self.enable_logging:
            logger.info(f"🔧 Initializing LiveCamera: {width}×{height} @ {fps} fps")

        # Motion detection setup
        self.setup_motion_detection()

        # Initialize camera
        if self.initialize_camera():
            # Start capture loop thread
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.is_running = True
            self.capture_thread.start()

            # Start detection loop thread
            self.detection_running = True
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()

            if self.enable_logging:
                logger.info("✅ LiveCamera initialized successfully")
        else:
            if self.enable_logging:
                logger.error("❌ LiveCamera initialization failed")
            raise Exception("Failed to initialize camera")

    def setup_motion_detection(self):
        """Initialize motion detection background subtractor."""
        try:
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                detectShadows=True,
                varThreshold=16,
                history=200
            )
            if self.enable_logging:
                logger.info("✅ Motion detection initialized")
        except Exception as e:
            if self.enable_logging:
                logger.error(f"⚠️ Motion detection setup error: {e}")
            self.motion_detection_enabled = False

    def initialize_camera(self):
        """Initialize the camera with optimized settings for higher FPS."""
        try:
            if self.enable_logging:
                logger.info(f"🔌 Connecting to camera {self.camera_index}...")

            if self.cap is not None:
                self.cap.release()
                time.sleep(0.1)

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

            # Set camera properties
            props = [
                (cv2.CAP_PROP_FRAME_WIDTH, self.width),
                (cv2.CAP_PROP_FRAME_HEIGHT, self.height),
                (cv2.CAP_PROP_FPS, self.fps),
                (cv2.CAP_PROP_BUFFERSIZE, 1),
                (cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')),
            ]
            for prop, value in props:
                try:
                    self.cap.set(prop, value)
                except Exception:
                    pass

            # Quick test capture
            for attempt in range(3):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                        self.raw_frame = frame.copy()
                    if self.enable_logging:
                        logger.info(f"✅ Camera test successful – frame size: {frame.shape}")
                    return True
                time.sleep(0.05)

            return False

        except Exception as e:
            if self.enable_logging:
                logger.error(f"❌ Camera initialization error: {e}")
            return False

    def _capture_loop(self):
        """Grab frames as fast as possible (up to target FPS)."""
        if self.enable_logging:
            logger.info("🎬 Capture loop started")

        target_interval = 1.0 / self.fps
        last_capture = 0.0

        while self.is_running:
            try:
                now = time.time()
                if now - last_capture < target_interval:
                    time.sleep(0.001)
                    continue

                if self.cap is None or not self.cap.isOpened():
                    if not self.reconnect_camera():
                        time.sleep(0.1)
                        continue

                ret, frame = self.cap.read()
                if not ret or frame is None:
                    self.error_count += 1
                    if self.error_count >= self.max_errors:
                        if self.enable_logging:
                            logger.warning("❌ Too many capture errors, attempting reconnect...")
                        self.reconnect_camera()
                        self.error_count = 0
                    continue

                with self.frame_lock:
                    self.current_frame = frame.copy()
                    self.raw_frame = frame.copy()

                self.frame_count += 1
                self.error_count = 0
                self.fps_counter.append(now)

                # Increment internal counter for optional skipping logic
                self._internal_frame_counter += 1

                last_capture = now

                # Periodic logging every ~30 seconds
                if self.enable_logging and (self.frame_count % (self.fps * 30) == 0):
                    actual_fps = self.get_actual_fps()
                    logger.info(f"📊 Frames captured: {self.frame_count}, actual FPS ≈ {actual_fps:.1f}")

            except Exception as e:
                self.error_count += 1
                if self.enable_logging:
                    logger.error(f"❌ Capture loop error: {e}")
                if self.error_count >= self.max_errors:
                    self.reconnect_camera()
                    self.error_count = 0

        if self.enable_logging:
            logger.info("🛑 Capture loop stopped")

    def _detection_loop(self):
        """
        Separate thread that continuously runs motion detection on the latest raw frame.
        Only processes every motion_check_interval frames to reduce overhead.
        """
        if self.enable_logging:
            logger.info("🔍 Detection loop started")
        last_checked_frame = 0

        while self.detection_running:
            if not self.motion_detection_enabled or self.background_subtractor is None:
                time.sleep(0.01)
                continue

            with self.frame_lock:
                frame = self.raw_frame.copy() if self.raw_frame is not None else None

            if frame is None:
                time.sleep(0.005)
                continue

            # Only run detection on every Nth frame
            if self._internal_frame_counter >= last_checked_frame + self.motion_check_interval:
                last_checked_frame = self._internal_frame_counter
                self._run_fast_motion_detection(frame)

            # Short sleep to prevent busy‐loop
            time.sleep(0.005)

        if self.enable_logging:
            logger.info("🛑 Detection loop stopped")

    def _run_fast_motion_detection(self, frame):
        """
        Fast motion detection on a downscaled, grayscale frame.
        """
        try:
            # 1) Downscale and convert to grayscale
            small = cv2.resize(frame, (self._motion_scale_w, self._motion_scale_h), interpolation=cv2.INTER_LINEAR)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            # 2) Apply background subtractor
            fg_mask = self.background_subtractor.apply(gray, learningRate=self.motion_sensitivity / 1000.0)

            # 3) Simple morphology (one open + one close)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self._fast_kernel)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self._fast_kernel)

            # 4) Find contours on the small mask
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            motion_areas = []
            total_motion_area = 0

            scale_x = frame.shape[1] / float(self._motion_scale_w)
            scale_y = frame.shape[0] / float(self._motion_scale_h)
            area_scale = scale_x * scale_y

            for cnt in contours:
                area_small = cv2.contourArea(cnt)
                if area_small * area_scale > self.motion_threshold:
                    x_s, y_s, w_s, h_s = cv2.boundingRect(cnt)
                    x = int(x_s * scale_x)
                    y = int(y_s * scale_y)
                    w_box = int(w_s * scale_x)
                    h_box = int(h_s * scale_y)
                    area_full = int(area_small * area_scale)
                    motion_areas.append((x, y, w_box, h_box, area_full))
                    total_motion_area += area_full

            motion_detected = (len(motion_areas) > 0 and total_motion_area > self.motion_threshold)

            now = time.time()
            if motion_detected and (now - self.last_motion_time) > self.motion_cooldown:
                self.motion_detected = True
                self.motion_areas = motion_areas
                self.last_motion_time = now
                if self.enable_logging:
                    logger.info(
                        f"🚨 Fast motion detected: regions={len(motion_areas)}, total_area={total_motion_area}"
                    )
            elif not motion_detected and (now - self.last_motion_time) > self.motion_cooldown:
                self.motion_detected = False
                self.motion_areas = []

        except Exception as e:
            if self.enable_logging:
                logger.error(f"⚠️ Fast motion detection error: {e}")

    def get_actual_fps(self):
        """Compute actual FPS over the last few timestamps."""
        if len(self.fps_counter) < 2:
            return 0.0
        time_span = self.fps_counter[-1] - self.fps_counter[0]
        if time_span > 0:
            return (len(self.fps_counter) - 1) / time_span
        return 0.0

    def toggle_motion_detection(self):
        """Toggle motion detection on or off."""
        self.motion_detection_enabled = not self.motion_detection_enabled
        status = "enabled" if self.motion_detection_enabled else "disabled"
        if self.enable_logging:
            logger.info(f"🚨 Motion detection {status}")
        return self.motion_detection_enabled

    def set_motion_sensitivity(self, sensitivity):
        """Set motion detection sensitivity (1–100)."""
        self.motion_sensitivity = max(1, min(100, sensitivity))
        if self.enable_logging:
            logger.info(f"🔧 Motion sensitivity set to {self.motion_sensitivity}")

    def set_motion_threshold(self, threshold):
        """Set minimum area threshold for motion detection."""
        self.motion_threshold = max(100, threshold)
        if self.enable_logging:
            logger.info(f"🔧 Motion threshold set to {self.motion_threshold}")

    def is_motion_detected(self):
        """Query whether motion was just detected."""
        return self.motion_detected

    def get_motion_areas(self):
        """Get the list of bounding boxes/areas for motion."""
        return self.motion_areas.copy() if self.motion_areas else []

    def get_current_frame(self, security_overlay=True):
        """Return the most recent frame (with optional overlay)."""
        with self.frame_lock:
            if self.current_frame is None:
                return None
            frame = self.current_frame.copy()
        if security_overlay:
            return self.add_security_overlay(frame)
        return frame

    def read_frame(self, security_overlay=True):
        """OpenCV‐style read(): returns (bool, frame)."""
        with self.frame_lock:
            if self.current_frame is None:
                return False, None
            frame = self.current_frame.copy()
        if security_overlay:
            return True, self.add_security_overlay(frame)
        return True, frame

    def read(self):
        """Alias for read_frame()."""
        return self.read_frame()

    def reconnect_camera(self):
        """Attempt to reinitialize the camera if it was lost."""
        if self.enable_logging:
            logger.info("🔄 Reconnecting camera...")
        try:
            if self.cap is not None:
                self.cap.release()
                time.sleep(0.2)
            return self.initialize_camera()
        except Exception as e:
            if self.enable_logging:
                logger.error(f"❌ Reconnection error: {e}")
            return False

    def get_stats(self):
        """Return a dictionary of runtime stats (frame count, fps, errors, etc.)."""
        actual_fps = self.get_actual_fps()
        uptime = time.time() - self.start_time
        return {
            'frame_count': self.frame_count,
            'error_count': self.error_count,
            'actual_fps': actual_fps,
            'target_fps': self.fps,
            'is_running': self.is_running,
            'camera_open': (self.cap is not None and self.cap.isOpened()) if self.cap else False,
            'has_current_frame': self.current_frame is not None,
            'has_raw_frame': self.raw_frame is not None,
            'motion_detection_enabled': self.motion_detection_enabled,
            'motion_detected': self.motion_detected,
            'motion_areas_count': len(self.motion_areas),
            'motion_threshold': self.motion_threshold,
            'motion_sensitivity': self.motion_sensitivity,
            'last_motion_time': self.last_motion_time,
            'uptime': uptime,
            'width': self.width,
            'height': self.height,
        }

    def record_clip(self, duration=5.0, record_fps=None):
        """
        Record a short MP4 clip (using the current frames).
        Defaults to min(self.fps, 30) if no record_fps is provided.
        """
        if record_fps is None:
            record_fps = min(self.fps, 30)

        try:
            filename = f'clip_{int(time.time())}.mp4'
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')

            test = self.get_current_frame(security_overlay=False)
            if test is None:
                return None
            h, w = test.shape[:2]
            out = cv2.VideoWriter(filename, fourcc, record_fps, (w, h))

            start_t = time.time()
            frame_interval = 1.0 / record_fps
            last_frame_time = 0

            if self.enable_logging:
                logger.info(f"🎬 Recording {duration}s clip at {record_fps} fps → {filename}")

            while time.time() - start_t < duration:
                t_now = time.time()
                if t_now - last_frame_time < frame_interval:
                    time.sleep(0.001)
                    continue
                frame = self.get_current_frame(security_overlay=False)
                if frame is not None:
                    out.write(frame)
                    last_frame_time = t_now

            out.release()
            if self.enable_logging:
                logger.info(f"✅ Clip recorded: {filename}")
            return filename

        except Exception as e:
            if self.enable_logging:
                logger.error(f"❌ Recording error: {e}")
            return None

    def add_security_overlay(self, frame):
        """
        Add a “security‐camera” overlay (timestamp, motion indicators, etc.). 
        """
        h, w = frame.shape[:2]

        # Draw translucent black bars at top and bottom
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 35), (0, 0, 0), -1)
        cv2.rectangle(overlay, (0, h - 35), (w, h), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)

        # Top‐left: camera ID
        camera_id = f"CAM-{self.camera_index:02d}"
        cv2.putText(frame, camera_id, (10, 20),
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)

        # Top‐left: REC dot + text
        cv2.circle(frame, (100, 15), 5, (0, 0, 255), -1)
        cv2.putText(frame, "REC", (115, 20),
                    cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 255), 1)

        # Top‐center: motion status
        if self.motion_detection_enabled:
            color = (0, 0, 255) if self.motion_detected else (0, 255, 0)
            text = "MOTION ALERT" if self.motion_detected else "MOTION ON"
            sz = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)[0]
            x_center = (w - sz[0]) // 2
            cv2.putText(frame, text, (x_center, 20),
                        cv2.FONT_HERSHEY_DUPLEX, 0.5, color, 1)
            cv2.circle(frame, (x_center - 15, 15), 4, color, -1)

        # Top‐right: resolution
        res_text = f"{w}×{h}"
        sz = cv2.getTextSize(res_text, cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)[0]
        cv2.putText(frame, res_text, (w - sz[0] - 10, 20),
                    cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

        # Draw bounding boxes if motion detected
        if self.motion_detected and self.motion_areas:
            for (x, y, w_box, h_box, area) in self.motion_areas:
                cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), (0, 0, 255), 2)
                cv2.putText(frame, f"MOTION: {int(area)}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Bottom‐left: timestamp
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cv2.putText(frame, now, (10, h - 10),
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)

        # Bottom‐right: frame counter
        counter_text = f"FRAME: {self.frame_count:08d}"
        sz = cv2.getTextSize(counter_text, cv2.FONT_HERSHEY_DUPLEX, 0.4, 1)[0]
        cv2.putText(frame, counter_text, (w - sz[0] - 10, h - 10),
                    cv2.FONT_HERSHEY_DUPLEX, 0.4, (255, 255, 255), 1)

        # Corner brackets (turn red if motion)
        bracket_color = (0, 255, 0) if not self.motion_detected else (0, 0, 255)
        bsize = 20
        bthick = 2
        # Top-left
        cv2.line(frame, (5, 40), (5, 40 + bsize), bracket_color, bthick)
        cv2.line(frame, (5, 40), (5 + bsize, 40), bracket_color, bthick)
        # Top-right
        cv2.line(frame, (w - 5, 40), (w - 5, 40 + bsize), bracket_color, bthick)
        cv2.line(frame, (w - 5, 40), (w - 5 - bsize, 40), bracket_color, bthick)
        # Bottom-left
        cv2.line(frame, (5, h - 40), (5, h - 40 - bsize), bracket_color, bthick)
        cv2.line(frame, (5, h - 40), (5 + bsize, h - 40), bracket_color, bthick)
        # Bottom-right
        cv2.line(frame, (w - 5, h - 40), (w - 5, h - 40 - bsize), bracket_color, bthick)
        cv2.line(frame, (w - 5, h - 40), (w - 5 - bsize, h - 40), bracket_color, bthick)

        return frame

    def is_opened(self):
        """Return True if camera is opened."""
        return (self.cap is not None and self.cap.isOpened()) if self.cap else False

    def stop(self):
        """Stop capture and detection threads and release resources."""
        if self.enable_logging:
            logger.info("🛑 Stopping camera...")

        # Stop capture loop
        self.is_running = False
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)

        # Stop detection loop
        self.detection_running = False
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=1.0)

        if self.cap and self.cap.isOpened():
            self.cap.release()

        if self.enable_logging:
            logger.info("✅ Camera stopped")

    def __del__(self):
        """Ensure cleanup on deletion."""
        try:
            self.stop()
        except Exception:
            pass

def take_snapshot(security_overlay=True):
    """
    Standalone function to grab one frame from default camera (index 0),
    apply a quick overlay, and return it.
    """
    logger.info("📸 Taking security camera snapshot...")
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None

        # Lower‐res for a quick snapshot
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        time.sleep(0.2)  # Warm up

        for _ in range(3):
            ret, frame = cap.read()
            if ret and frame is not None:
                cap.release()
                if security_overlay:
                    h, w = frame.shape[:2]
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (0, 0), (w, 35), (0, 0, 0), -1)
                    cv2.rectangle(overlay, (0, h - 35), (w, h), (0, 0, 0), -1)
                    frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)

                    cv2.putText(frame, "CAM-00", (10, 20),
                               cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)
                    cv2.circle(frame, (100, 15), 5, (0, 0, 255), -1)
                    cv2.putText(frame, "REC", (115, 20),
                               cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 255), 1)

                    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    cv2.putText(frame, now, (10, h - 10),
                               cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)

                    bracket_color = (0, 255, 0)
                    bsize = 20
                    # Top-left
                    cv2.line(frame, (5, 40), (5, 40 + bsize), bracket_color, 2)
                    cv2.line(frame, (5, 40), (5 + bsize, 40), bracket_color, 2)
                    # Top-right
                    cv2.line(frame, (w - 5, 40), (w - 5, 40 + bsize), bracket_color, 2)
                    cv2.line(frame, (w - 5, 40), (w - 25, 40), bracket_color, 2)
                    # Bottom-left
                    cv2.line(frame, (5, h - 40), (5, h - 40 - bsize), bracket_color, 2)
                    cv2.line(frame, (5, h - 40), (25, h - 40), bracket_color, 2)
                    # Bottom-right
                    cv2.line(frame, (w - 5, h - 40), (w - 5, h - 40 - bsize), bracket_color, 2)
                    cv2.line(frame, (w - 5, h - 40), (w - 25, h - 40), bracket_color, 2)

                logger.info("✅ Security camera snapshot captured")
                return frame
            time.sleep(0.05)

        cap.release()
        return None

    except Exception as e:
        logger.error(f"❌ Snapshot error: {e}")
        return None

# Compatibility alias
Camera = LiveCamera
