# d:\Smart Ambulance Traffic\core\vision.py

import cv2
import threading
import time
from ultralytics import YOLO
import constants

class VisionProcessor:
    """
    Handles video capture, frame resizing, and object detection.
    """
    def __init__(self, video_source=0):
        self.model = YOLO(constants.YOLO_MODEL_PATH)
        self.video_source = video_source
        self.cap = cv2.VideoCapture(self.video_source)
        if not self.cap.isOpened():
            raise IOError(f"Cannot open video source: {video_source}")

        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        aspect_ratio = self.frame_height / self.frame_width
        self.new_height = int(constants.RESIZE_WIDTH * aspect_ratio)

        # --- Threading for Lag-Free Video ---
        self.latest_frame = None
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        """Reads frames from the video source in a background thread."""
        while self.running:
            success, frame = self.cap.read()
            if not success:
                # If it's a video file, it might have ended.
                if self.video_source != 0:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop video
                    continue
                else: # If it's a webcam, wait and retry
                    time.sleep(0.5)
                    continue
            
            with self.lock:
                self.latest_frame = frame
        self.cap.release()

    def read(self):
        """Returns the latest frame read by the background thread."""
        with self.lock:
            if self.latest_frame is None:
                return False, None
            return True, self.latest_frame.copy()

    def process_frame(self):
        """
        Reads a frame, performs detection, and returns results.
        Returns a tuple: (annotated_frame, vehicle_count, ambulance_detected)
        """
        success, frame = self.read()
        if not success:
            return None, 0, False

        resized_frame = cv2.resize(frame, (constants.RESIZE_WIDTH, self.new_height))
        results = self.model(resized_frame, verbose=False)
        
        # By default, plot() draws boxes, confidence scores, and labels.
        # This is more explicit and ensures you see the detections.
        annotated_frame = results[0].plot()

        vehicle_count = 0
        ambulance_detected = False
        for box in results[0].boxes:
            label = self.model.names[int(box.cls[0])]
            if label in constants.VEHICLE_CLASSES: vehicle_count += 1
            if label in constants.EMERGENCY_VEHICLE_CLASSES: ambulance_detected = True

        return annotated_frame, vehicle_count, ambulance_detected

    def stop(self):
        """Signals the reader thread to stop."""
        self.running = False
        self.thread.join()