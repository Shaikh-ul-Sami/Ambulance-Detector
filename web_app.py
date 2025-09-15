# d:\Smart Ambulance Traffic\web_app.py

import argparse
import cv2
import threading
import time # CRITICAL FIX: This was missing, causing the app to crash.
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

# ===================================================================
# SHARED STATE & APPLICATION SETUP
# ===================================================================
app = Flask(__name__)
state_lock = threading.Lock() # To safely update state from multiple threads

# --- Global Instance of the Traffic System ---
traffic_system = TrafficSystem()
last_frames = {} # NEW: Dictionary to hold the latest frame from each camera
stop_event = threading.Event() # NEW: Global event to signal threads to stop

def select_video_sources_cli():
    """A command-line fallback for selecting video files."""
    selected_sources = {}
    print("\n--- GUI Dialog Failed. Using Command-Line Input ---")
    print("Please enter the full path for each video file below.")
    print("(You can drag and drop the file into the terminal window)\n")

    for lane in constants.LANES:
        while True:
            # The .strip('"') is important for drag-and-drop on Windows
            filepath = input(f"Enter path for {lane.upper()} lane: ").strip().strip('"')
            if os.path.exists(filepath):
                selected_sources[lane] = filepath
                print(f"  ✅ {lane.title()} Lane: {os.path.basename(filepath)}")
                break
            else:
                print(f"  ❌ ERROR: File not found at '{filepath}'. Please try again.")
    return selected_sources

def select_video_sources():
    """Opens file dialogs for the user to select a video for each lane."""
    # Use Python's built-in tkinter for better reliability than tinyfiledialogs
    try:
        from tkinter import Tk, filedialog
        # We need to create a root window but we don't want to see it
        root = Tk()
        root.withdraw()

        selected_sources = {}
        print("\n--- Please Select Video Files for Each Lane ---")
        for lane in constants.LANES:
            filepath = filedialog.askopenfilename(
                title=f"Select video for {lane.upper()} lane",
                filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv"), ("All Files", "*.*")]
            )
            if not filepath:
                print(f"❌ Canceled selection for {lane} lane. Exiting application.")
                return None
            selected_sources[lane] = filepath
            print(f"  ✅ {lane.title()} Lane: {os.path.basename(filepath)}")
        root.destroy() # Clean up the hidden window
        return selected_sources
    except Exception as e:
        print(f"Warning: Could not open GUI file dialog ({e}).")
        return select_video_sources_cli()

def pre_flight_checks(video_sources):
    """Checks for essential files before starting the application."""
    print("--- Running Pre-flight Checks ---")
    # 1. Check for YOLO model file
    if not os.path.exists(constants.YOLO_MODEL_PATH):
        print(f"❌ ERROR: YOLO model file not found at '{constants.YOLO_MODEL_PATH}'")
        print("Please download 'yolov8n.pt' and place it in the main project folder.")
        return False
    # 2. Check for video file (if not using webcam)
    for lane, source in video_sources.items():
        if not str(source).isdigit() and not os.path.exists(source):
            print(f"❌ ERROR: Video file for lane '{lane}' not found at '{source}'")
            print("Please make sure the video file exists or use a valid camera index (e.g., 0).")
            return False

    print("✅ All checks passed.")
    return True

def system_logic_thread():
    """
    A dedicated thread to run the main traffic system logic (the "tick").
    This decouples the core logic from any single video processing thread.
    """
    print("⚙️ System logic thread started.")
    tick_interval = 0.1 # Run the logic 10 times per second
    while not stop_event.is_set():
        with state_lock:
            traffic_system.tick()
        time.sleep(tick_interval)
    print("System logic thread stopped.")


# ===================================================================
# BACKGROUND PROCESSING THREAD
# ===================================================================
def video_processing_thread(lane, video_source):
    """The main background thread for video capture, detection, and state updates."""
    global last_frames, stop_event
    try:
        vision_processor = VisionProcessor(video_source=video_source, lane_name=lane)
    except IOError as e:
        print(f"---!!! ERROR !!!--- Could not start video processing: {e}")
        return

    video_fps = vision_processor.cap.get(cv2.CAP_PROP_FPS)
    if not video_fps or video_fps <= 0:
        video_fps = 30 # Fallback for webcams
    
    frame_duration = 1 / video_fps
    frame_count = 0

    while not stop_event.is_set():
        start_time = time.time()

        # --- THE HOLISTIC FIX: A consistent order of operations on every frame ---

        # 1. Always get the latest frame from the camera.
        success, frame = vision_processor.read()
        if not success or frame is None:
            # If the video ends or camera fails, show a "SIGNAL LOST" message.
            with state_lock:
                if last_frames.get(lane) is not None:
                    lost_signal_frame = last_frames[lane].copy()
                    # Add a semi-transparent overlay
                    overlay = lost_signal_frame.copy()
                    cv2.rectangle(overlay, (0, 0), (lost_signal_frame.shape[1], lost_signal_frame.shape[0]), (0, 0, 0), -1)
                    lost_signal_frame = cv2.addWeighted(overlay, 0.5, lost_signal_frame, 0.5, 0)
                    # Add text
                    cv2.putText(lost_signal_frame, "SIGNAL LOST", (50, lost_signal_frame.shape[0] // 2), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                    last_frames[lane] = lost_signal_frame
            stop_event.set() # Stop this thread
            print(f"---! WARNING !--- Signal lost for lane '{lane}'. Thread will stop.")
            continue

        # 2. On Nth frames, perform expensive detection and update the system's knowledge.
        if frame_count % constants.PROCESS_EVERY_NTH_FRAME == 0:
            annotated_frame, vehicle_count, ambulance_detected = vision_processor.process_frame()
            with state_lock:
                # Update the system with what this lane sees
                traffic_system.update_detection_results(lane, vehicle_count, ambulance_detected)
        else:
            # If not processing, just resize the raw frame for display
            annotated_frame = cv2.resize(frame, (constants.RESIZE_WIDTH, vision_processor.new_height))

        # 3. Draw the current light state for THIS lane onto the frame and store it.
        # This is now done on every frame to ensure the display is always up-to-date.
        with state_lock:
            display_frame = traffic_system.draw_lights_on_frame(annotated_frame, lane)
            if display_frame is not None:
                last_frames[lane] = display_frame.copy()

        frame_count += 1
        # Synchronize to the video's original FPS
        elapsed_time = time.time() - start_time
        sleep_time = max(0, frame_duration - elapsed_time)
        time.sleep(sleep_time)
    
    vision_processor.stop()
    print(f"Video processing thread for lane '{lane}' stopped.")

# ===================================================================
# FLASK ROUTES
# ===================================================================
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

def generate_frames_for_lane(lane):
    """Generator function that yields JPEG-encoded video frames."""
    while not stop_event.is_set():
        frame_to_send = None
        with state_lock:
            # Get the latest frame for the requested lane
            if lane in last_frames and last_frames[lane] is not None:
                frame_to_send = last_frames[lane].copy()
        
        if frame_to_send is not None:
            (flag, encodedImage) = cv2.imencode(".jpg", frame_to_send)
            if flag:
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
                      bytearray(encodedImage) + b'\r\n')
        
        # A small sleep prevents this loop from spinning too fast if a frame isn't ready
        # or if the client disconnects.
        time.sleep(0.07) # Target ~15 FPS for the web feed to save encoding CPU

@app.route('/video_feed/<lane>')
def video_feed(lane):
    """A unique video feed endpoint for each lane."""
    if lane not in constants.LANES:
        return "Invalid lane specified", 404
    return Response(generate_frames_for_lane(lane), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/events')
def events():
    """Server-Sent Events endpoint for real-time status messages."""
    def generate_events():
        while not stop_event.is_set():
            with state_lock:
                try:
                    msg = traffic_system.event_messages.popleft()
                    yield f"data: {msg}\n\n"
                except IndexError:
                    pass # Queue is empty, do nothing
            time.sleep(0.5)
    return Response(generate_events(), mimetype='text/event-stream')

@app.route('/status')
def status():
    """Provides the current state of the traffic system as JSON."""
    with state_lock:
        # Create a dictionary with the states of all lights and other info
        system_status = {
            'lights': traffic_system.light_states,
            'density_per_lane': traffic_system.density_per_lane,
            'manual_mode': traffic_system.manual_override
        }
    return jsonify(system_status)

@app.route('/manual_override', methods=['POST'])
def manual_override():
    """Endpoint to handle manual control of the traffic lights from the UI."""
    data = request.get_json()
    action = data.get('action')
    
    with state_lock:
        if action == 'set_lane':
            lane = data.get('lane')
            state = data.get('state')
            if lane in traffic_system.light_states and state in ['RED', 'YELLOW', 'GREEN']:
                traffic_system.manual_override = True
                traffic_system.light_states[lane] = state
                traffic_system.event_messages.append(f"🕹️ Manual: Set {lane.upper()} to {state}")

        elif action == 'auto':
            traffic_system.set_auto_mode()

    return {"status": "ok"}

# ===================================================================
# MAIN EXECUTION
# ===================================================================
if __name__ == '__main__':
    # --- Step 1: Get video sources from the user using native file dialogs ---
    user_selected_videos = select_video_sources()
    
    if not user_selected_videos:
        sys.exit(1) # Exit if user cancelled selection

    # --- Step 2: Run Pre-flight Checks on selected files ---
    if not pre_flight_checks(user_selected_videos):
        sys.exit(1) # Stop if checks fail

    try:
        # --- Step 3: Start Background Threads ---
        print("Starting background threads...")
        
        # 1. Video Processing Threads (one for each camera)
        processing_threads = []
        # Use the video files selected by the user
        for lane, source in user_selected_videos.items():
            thread = threading.Thread(target=video_processing_thread, args=(lane, source))
            thread.start()
            processing_threads.append(thread)
        
        # 2. System Logic Thread (the new "heartbeat")
        logic_thread = threading.Thread(target=system_logic_thread)
        logic_thread.start()

        # 2. Audio Listener Thread
        def on_siren_detected():
            with state_lock:
                traffic_system.siren_heard = True
        
        audio_thread = threading.Thread(target=audio_listener_thread, args=(on_siren_detected, stop_event))
        audio_thread.start()

        # --- Step 4: Run Flask App ---
        print("Flask server starting... Open http://127.0.0.1:5000 in your browser.")
        print("Press CTRL+C to stop the server.")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

    except KeyboardInterrupt:
        print("\nCTRL+C detected. Shutting down gracefully...")
    finally:
        # --- Signal all threads to stop ---
        stop_event.set()
        print("Waiting for background threads to finish...")
        for thread in processing_threads:
            thread.join()
        if 'logic_thread' in locals(): logic_thread.join()
        if 'audio_thread' in locals(): audio_thread.join()
        print("All threads stopped. Exiting.")
