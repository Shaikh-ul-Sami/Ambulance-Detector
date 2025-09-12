# d:\Smart Ambulance Traffic\core\constants.py

# ===================================================================
# CORE CONFIGURATION
# This file contains all shared settings for the traffic system.
# ===================================================================

# --- Model Configuration ---
YOLO_MODEL_PATH = "yolov8n.pt"

PROCESS_EVERY_NTH_FRAME = 5 
RESIZE_WIDTH = 640          

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