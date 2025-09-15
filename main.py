# ===================================================================
# ALL IMPORTS
# ===================================================================
import cv2
import threading
import time

# Add the project root to the Python path to allow for absolute imports
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from audio import audio_listener_thread
from vision import VisionProcessor
from traffic_system import TrafficSystem
import constants

# Conditionally import Pygame for graceful error handling if it's not installed
try:
    import pygame
    from Simulation.traffic_gui import TrafficLight, BLACK, WHITE
except ImportError:
    print("Warning: Pygame or traffic_gui.py not found. GUI simulation cannot run.")
    pygame = None
    TrafficLight = None

# ===================================================================
# SHARED STATE & APPLICATION SETUP
# ===================================================================
state_lock = threading.Lock()
traffic_system = TrafficSystem()
last_frames = {lane: None for lane in constants.LANES}
stop_event = threading.Event()

def select_video_sources_cli():
    """A command-line fallback for selecting video files."""
    selected_sources = {}
    print("\n--- GUI Dialog Failed. Using Command-Line Input ---")
    print("Please enter the full path for each video file below.")
    print("(You can drag and drop the file into the terminal window)\n")

    for lane in constants.LANES:
        while True:
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
    if not os.path.exists(constants.YOLO_MODEL_PATH):
        print(f"❌ ERROR: YOLO model file not found at '{constants.YOLO_MODEL_PATH}'")
        return False
    for lane, source in video_sources.items():
        if not str(source).isdigit() and not os.path.exists(source):
            print(f"❌ ERROR: Video file for lane '{lane}' not found at '{source}'")
            return False
    print("✅ All checks passed.")
    return True

def handle_input():
    """Processes Pygame events, like closing the window."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
    return True

def system_logic_thread():
    """Dedicated thread to run the main traffic system logic (the "tick")."""
    print("⚙️ System logic thread started.")
    while not stop_event.is_set():
        with state_lock:
            traffic_system.tick()
        time.sleep(0.1)
    print("System logic thread stopped.")

def video_processing_thread(lane, video_source):
    """Background thread for video capture, detection, and state updates for a single lane."""
    global last_frames
    try:
        vision_processor = VisionProcessor(video_source=video_source, lane_name=lane)
    except IOError as e:
        print(f"---!!! ERROR !!!--- Could not start video processing for {lane}: {e}")
        return

    video_fps = vision_processor.cap.get(cv2.CAP_PROP_FPS)
    if not video_fps or video_fps <= 0:
        video_fps = 30 # Fallback for webcams or problematic files
    frame_duration = 1 / video_fps

    frame_count = 0
    while not stop_event.is_set():
        start_time = time.time()

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
            print(f"---! WARNING !--- Signal lost for lane '{lane}'. Thread will stop.")
            break # Exit the loop to stop this thread
            continue

        if frame_count % constants.PROCESS_EVERY_NTH_FRAME == 0:
            annotated_frame, vehicle_count, ambulance_detected = vision_processor.process_frame()
            with state_lock:
                traffic_system.update_detection_results(lane, vehicle_count, ambulance_detected)
        else:
            # Just resize the raw frame for display if not processing
            annotated_frame = cv2.resize(frame, (constants.RESIZE_WIDTH, vision_processor.new_height))

        with state_lock:
            # Pass the lane name to draw only the relevant light indicator
            display_frame = traffic_system.draw_lights_on_frame(annotated_frame, lane)
            if display_frame is not None:
                last_frames[lane] = display_frame.copy()
        
        frame_count += 1
        # Synchronize to the video's original FPS to save CPU
        elapsed_time = time.time() - start_time
        sleep_time = max(0, frame_duration - elapsed_time)
        time.sleep(sleep_time)
    
    vision_processor.stop()
    print(f"Video processing thread for {lane} stopped.")

def draw_screen(screen, traffic_lights, fonts, clock):
    """Draws all elements onto the screen."""
    screen.fill(BLACK)
    
    # Define positions for the 2x2 video grid
    positions = {
        'north': (0, 0),
        'south': (constants.RESIZE_WIDTH, 0),
        'east': (0, 360), # Assuming a standard 16:9 aspect ratio (640x360)
        'west': (constants.RESIZE_WIDTH, 360)
    }

    with state_lock:
        for lane, frame in last_frames.items():
            if frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_pygame = pygame.image.frombuffer(frame_rgb.tobytes(), frame.shape[1::-1], "RGB")
                screen.blit(frame_pygame, positions[lane])

    # Draw traffic lights and their labels
    with state_lock:
        for name, light in traffic_lights.items():
            state = traffic_system.light_states[name].lower()
            light.set_light(state)
            light.draw(screen)
            label_text = fonts['small'].render(name.upper(), True, WHITE)
            label_pos = label_text.get_rect(center=(light.x, light.y - 40))
            screen.blit(label_text, label_pos)

        # Draw status dashboard text
        status_y = 20
        for lane, count in traffic_system.density_per_lane.items():
            vehicle_text = fonts['normal'].render(f"{lane.title()} Vehicles: {count}", True, WHITE)
            screen.blit(vehicle_text, (constants.RESIZE_WIDTH * 2 + 10, status_y))
            status_y += 30
        
        status_y += 10
        reason = "Normal Operation"
        if traffic_system.siren_heard: reason = "Siren Detected"
        elif traffic_system.density_alert_sent: reason = "High Density"
        reason_text = fonts['normal'].render(f"Reason: {reason}", True, WHITE)
        screen.blit(reason_text, (constants.RESIZE_WIDTH * 2 + 10, status_y))

    fps_text = fonts['normal'].render(f"FPS: {clock.get_fps():.1f}", True, WHITE)
    screen.blit(fps_text, (constants.RESIZE_WIDTH * 2 + 10, status_y + 40))
        
    pygame.display.flip()

if __name__ == "__main__":
    user_selected_videos = select_video_sources()
    if not user_selected_videos:
        sys.exit(1)

    # --- Run Pre-flight Checks ---
    if not pre_flight_checks(user_selected_videos):
        sys.exit(1) # Stop if checks fail

    # Exit if Pygame is not available
    if not pygame or not TrafficLight:
        print("Exiting: Pygame is required for this local simulation.")
        sys.exit(1)

    # --- Start Background Threads ---
    print("Starting background threads...")
    processing_threads = []
    for lane, source in user_selected_videos.items():
        thread = threading.Thread(target=video_processing_thread, args=(lane, source))
        thread.start()
        processing_threads.append(thread)
    
    logic_thread = threading.Thread(target=system_logic_thread)
    logic_thread.start()
    
    def on_siren_detected():
        with state_lock:
            traffic_system.siren_heard = True
    
    audio_thread = threading.Thread(target=audio_listener_thread, args=(on_siren_detected, stop_event))
    audio_thread.start()

    # 2. Initialize Pygame and Fonts
    pygame.init()
    pygame.font.init()
    PANEL_WIDTH = 300
    # New screen size: 2 videos wide, 2 videos high, plus a side panel
    screen = pygame.display.set_mode((constants.RESIZE_WIDTH * 2 + PANEL_WIDTH, 360 * 2))
    pygame.display.set_caption("Smart Traffic Simulation")
    fonts = {
        'small': pygame.font.SysFont('Arial', 20, bold=True),
        'normal': pygame.font.SysFont('Arial', 24)
    }

    clock = pygame.time.Clock()

    # 3. Setup GUI Elements (Traffic Lights)
    traffic_lights = {}
    light_radius = 20
    panel_center_x = constants.RESIZE_WIDTH * 2 + PANEL_WIDTH // 2
    start_y = 400 # Adjusted Y position to be visible on screen

    for i, lane_name in enumerate(constants.LANES):
        y_pos = start_y + i * 100
        traffic_lights[lane_name] = TrafficLight(x=panel_center_x, y=y_pos, radius=light_radius)

    # 4. Main Application Loop
    running = True
    while running:
        running = handle_input()
        draw_screen(screen, traffic_lights, fonts, clock)
        clock.tick(30) # Redraw the screen at 30 FPS
        
    # 5. Cleanup on Exit
    print("\nShutdown signal received. Waiting for threads to finish...")
    stop_event.set()
    for thread in processing_threads: thread.join()
    logic_thread.join()
    audio_thread.join()
    pygame.quit()
    print("\nProgram finished.")