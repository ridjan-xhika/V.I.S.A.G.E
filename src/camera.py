import cv2
import threading
import time
import os
from tempfile import NamedTemporaryFile


latest_frame = None
frame_lock = threading.Lock()

def take_snapshot():
    with frame_lock:
        if latest_frame is None:
            return None
        return latest_frame.copy()

def record_clip(duration: float = 5.0, fps: int = 60) -> str:

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    with frame_lock:
        frame = latest_frame.copy() if latest_frame is not None else None
    if frame is None:
        raise RuntimeError("No camera frame available to record.")
    h, w = frame.shape[:2]

    tmp = NamedTemporaryFile(prefix="clip_", suffix=".mp4", delete=False)
    out = cv2.VideoWriter(tmp.name, fourcc, fps, (w, h))

    start = time.time()
    while time.time() - start < duration:
        with frame_lock:
            frm = latest_frame.copy() if latest_frame is not None else None
        if frm is not None:
            out.write(frm)
        time.sleep(1.0 / fps)

    out.release()
    return tmp.name

def LiveCamera():
    cap = cv2.VideoCapture(0)
    global latest_frame

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*'mpv4')
    out = cv2.VideoWriter('output.mp4', fourcc, 20.0, (frame_width, frame_height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        with frame_lock:
            latest_frame = frame
        cv2.imshow('Camera', frame)
        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()