# d:\Smart Ambulance Traffic\web_app.py

import cv2
import threading
import time
from flask import Flask, render_template, Response, request, jsonify
import sys
import os

# --- Add project root to path for imports ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from audio import audio_listener_thread
from vision import VisionProcessor
from traffic_system import TrafficSystem
import constants

# --- Video Source Configuration ---
VIDEO_PATH = "traffic_video.mp4" # Use 0 for webcam or "path/to/your/video.mp4" for a file

# ===================================================================
# SHARED STATE & APPLICATION SETUP
# ===================================================================
app = Flask(__name__)
state_lock = threading.Lock() # To safely update state from multiple threads

# --- Global Instance of the Traffic System ---
traffic_system = TrafficSystem()
last_frame = None # Global variable to hold the latest processed frame

# ===================================================================
# BACKGROUND PROCESSING THREAD
# ===================================================================
def video_processing_thread():
    global traffic_system, last_frame
    vision_processor = VisionProcessor(video_source=VIDEO_PATH)
    frame_count = 0

    while True:
        # Always get the latest raw frame
        success, frame = vision_processor.read()
        if not success:
            time.sleep(0.05)
            continue

        # Decide whether to process for objects or just display the frame
        if frame_count % constants.PROCESS_EVERY_NTH_FRAME == 0: # Process logic periodically
            # This re-reads the latest frame and performs detection
            processed_frame, vehicle_count, ambulance_detected = vision_processor.process_frame()
            if processed_frame is None: continue # Skip if processing failed
            with state_lock:
                traffic_system.update_detection_results(vehicle_count, ambulance_detected)
            annotated_frame = processed_frame # Use the frame with detection boxes
        else: # On non-processing frames, just use the raw frame
            annotated_frame = cv2.resize(frame, (constants.RESIZE_WIDTH, vision_processor.new_height))
        
        # --- Draw Status on Frame ---
        state = traffic_system.light_state
        color = (0, 255, 0) if state == 'GREEN' else (0, 255, 255) if state == 'YELLOW' else (0, 0, 255)
        
        # Draw a filled circle as a visual indicator for the light state
        cv2.circle(annotated_frame, (30, 30), 20, color, -1)
        cv2.circle(annotated_frame, (30, 30), 20, (255,255,255), 2) # White border

        # Draw text status next to the circle
        # cv2.putText(annotated_frame, f"Signal: {state.upper()}", (60, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
        cv2.putText(annotated_frame, f"Vehicles: {traffic_system.last_vehicle_count}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)


        with state_lock:
            last_frame = annotated_frame.copy()
        
        # Tick the system *after* preparing the frame for display.
        # This ensures the state change happens for the *next* frame.
        with state_lock:
            traffic_system.tick()

        frame_count += 1
        time.sleep(1/60) # Yield to other threads, aim for ~60fps display rate

# ===================================================================
# FLASK ROUTES
# ===================================================================
@app.route('/')
def index():
    return render_template('index.html')

def generate_frames():
    while True:
        with state_lock:
            if last_frame is None:
                continue
            (flag, encodedImage) = cv2.imencode(".jpg", last_frame)
            if not flag:
                continue
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')
        time.sleep(0.03) # 30 fps

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/events')
def events():
    def generate_events():
        while True:
            with state_lock:
                try:
                    # Use popleft() for efficient queue operation
                    msg = traffic_system.event_messages.popleft()
                except IndexError:
                    # Queue is empty, wait before checking again
                    time.sleep(0.5)
                    continue
            yield f"data: {msg}\n\n"
            time.sleep(0.5)
    return Response(generate_events(), mimetype='text/event-stream')

@app.route('/status')
def status():
    """Provides the current state of the traffic system as JSON."""
    with state_lock:
        # Create a dictionary with the states of all lights and other info
        system_status = {
            'lights': traffic_system.light_states,
            'vehicle_count': traffic_system.last_vehicle_count,
            'manual_mode': traffic_system.manual_override
        }
    return jsonify(system_status)

@app.route('/manual_override', methods=['POST'])
def manual_override():
    action = request.json.get('action')
    with state_lock:
        if action == 'force_green':
            traffic_system.manual_override = True
            for lane in traffic_system.light_states:
                traffic_system.light_states[lane] = 'GREEN'
            traffic_system.event_messages.append("🕹️ Manual Override: Signal GREEN")
        elif action == 'force_red':
            traffic_system.manual_override = True
            for lane in traffic_system.light_states:
                traffic_system.light_states[lane] = 'RED'
            traffic_system.event_messages.append("🕹️ Manual Override: Signal RED")
        elif action == 'auto':
            traffic_system.manual_override = False
            # Reset timers to allow natural flow
            for lane in traffic_system.light_states:
                traffic_system.light_states[lane] = 'YELLOW'
            traffic_system.yellow_light_timer = traffic_system._get_time_ms()
            traffic_system.event_messages.append("🕹️ Manual Override Disabled. Resuming Auto.")
    return {"status": "ok"}

# ===================================================================
# MAIN EXECUTION
# ===================================================================
if __name__ == '__main__':
    # Start the background thread for video processing
    processing_thread = threading.Thread(target=video_processing_thread, daemon=True)
    processing_thread.start()
    
    def on_siren_detected():
        with state_lock:
            traffic_system.siren_heard = True

    # Start the background thread for audio listening
    audio_thread = threading.Thread(target=audio_listener_thread, args=(on_siren_detected,), daemon=True)
    audio_thread.start()

    # Run the Flask app
    print("Flask server starting... Open http://127.0.0.1:5000 in your browser.")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
