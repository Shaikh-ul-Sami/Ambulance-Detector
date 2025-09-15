# d:\Smart Ambulance Traffic\core\constants.py

# ===================================================================
# CORE CONFIGURATION
# This file contains all shared settings for the traffic system.
# ===================================================================

# --- Model Configuration ---
YOLO_MODEL_PATH = "yolov8n.pt"

PROCESS_EVERY_NTH_FRAME = 15 # Process even fewer frames to save significant CPU
RESIZE_WIDTH = 480           # Smaller resolution for faster YOLO processing

# --- Siren Detection ---
SIREN_FREQUENCY_RANGE = (700, 1500)  
SIREN_LOUDNESS_THRESHOLD = 22.5
SIREN_DETECTION_WINDOW = 10
SIREN_CONFIRMATION_COUNT = 4

# --- Traffic & Vehicle Detection ---
HIGH_DENSITY_THRESHOLD = 10
VEHICLE_CLASSES = ['car', 'motorcycle', 'bus', 'truck']
EMERGENCY_VEHICLE_CLASSES = ['ambulance', 'fire truck', 'police car', 'bus', 'truck']

# --- Traffic Light Timings (in milliseconds) ---
GREEN_LIGHT_DURATION_DENSITY = 10000
YELLOW_LIGHT_DURATION = 3000
GREEN_LIGHT_GRACE_PERIOD = 4000 # Time to wait with low density before switching from green to yellow
RIGHT_TURN_YELLOW_DELAY = 1500  # How long after density drops that the right turn signal goes yellow. Must be < GREEN_LIGHT_GRACE_PERIOD

# --- Road Layout Configuration ---
LANES = ['north', 'south', 'east', 'west'] # Defines the lanes for a 4-way intersection.

# --- NEW: Multi-Camera Configuration ---
# Assign a video source to each lane.
# Use '0', '1', etc., for webcams, or a path to a video file.
VIDEO_SOURCES = {
    # Each lane is now assigned a unique video file.
    # Make sure these files exist in your project directory.
    'north': 'traffic_north.mp4',
    'south': 'traffic_south.mp4',
    'east': 'traffic_east.mp4',
    'west': 'traffic_west.mp4',
}