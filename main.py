# ===================================================================
# ALL IMPORTS
# ===================================================================
import pygame
import cv2
import threading
import sys

# Add the project root to the Python path to allow for absolute imports
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from audio import audio_listener_thread
from vision import VisionProcessor
from traffic_system import TrafficSystem
import constants
from Simulation.traffic_gui import TrafficLight, RED, YELLOW, GREEN, BLACK, WHITE # Import colors

# ===================================================================
# CONFIGURATION
# ===================================================================
VIDEO_PATH = "traffic_video.mp4" # Use 0 for webcam or "path/to/your/video.mp4" for a file

def main():
    print("===================================================================")
    print("NOTE: You are running main.py, the local Pygame simulation.")
    print("To run the web dashboard version, run 'python web_app.py'")
    print("===================================================================\n")
    
    traffic_system = TrafficSystem()

    def on_siren_detected():
        traffic_system.siren_heard = True
    stop_audio_event = threading.Event()
    listener_thread = threading.Thread(target=audio_listener_thread, args=(on_siren_detected, stop_audio_event), daemon=True)
    listener_thread.start()

    try:
        vision_processor = VisionProcessor(video_source=VIDEO_PATH)
    except IOError as e:
        print(f"Error initializing camera: {e}")
        return

    pygame.init()
    TRAFFIC_LIGHT_PANEL_WIDTH = 150
    screen = pygame.display.set_mode((constants.RESIZE_WIDTH + TRAFFIC_LIGHT_PANEL_WIDTH, vision_processor.new_height))
    pygame.display.set_caption("Live Ambulance Detection")
    
    running, frame_count = True, 0

    # Create three traffic lights for the display (Left, Straight, Right)
    light_radius = 20
    panel_center_x = constants.RESIZE_WIDTH + TRAFFIC_LIGHT_PANEL_WIDTH // 2
    screen_center_y = vision_processor.new_height // 2
    
    traffic_lights = {
        'left': TrafficLight(x=panel_center_x, y=screen_center_y - 120, radius=light_radius),
        'straight': TrafficLight(x=panel_center_x, y=screen_center_y, radius=light_radius),
        'right': TrafficLight(x=panel_center_x, y=screen_center_y + 120, radius=light_radius)
    }

    # NEW: Font for on-screen display
    pygame.font.init() # Initialize font module
    font_small = pygame.font.SysFont('Arial', 20, bold=True)
    font = pygame.font.SysFont('Arial', 24)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        annotated_frame, vehicle_count, ambulance_detected = None, 0, False
        if frame_count % constants.PROCESS_EVERY_NTH_FRAME == 0:
            annotated_frame, vehicle_count, ambulance_detected = vision_processor.process_frame()
            if annotated_frame is None: continue # Skip if frame read failed
            traffic_system.update_detection_results(vehicle_count, ambulance_detected)
        else:
            # For frames that are skipped, just read a new one without processing
            success, frame = vision_processor.read() # FIX: Use the threaded reader
            if not success or frame is None: continue
            annotated_frame = cv2.resize(frame, (constants.RESIZE_WIDTH, vision_processor.new_height))
        
        screen.fill(BLACK)
        frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        frame_pygame = pygame.image.frombuffer(frame_rgb.tobytes(), (constants.RESIZE_WIDTH, vision_processor.new_height), "RGB")
        screen.blit(frame_pygame, (0, 0))

        # 6. Draw the traffic lights and their labels
        for name, light in traffic_lights.items():
            state = traffic_system.light_states[name].lower()
            light.set_light(state)
            light.draw(screen)
            
            # Draw label for each light
            label_text = font_small.render(name.upper(), True, WHITE)
            label_pos = label_text.get_rect(center=(light.x, light.y - 40))
            screen.blit(label_text, label_pos)

        # 7. Draw the status dashboard text
        status_text_y_start = 20
        # --- Vehicle Count ---
        vehicle_text = font.render(f"Vehicles: {traffic_system.last_vehicle_count}", True, WHITE)
        screen.blit(vehicle_text, (constants.RESIZE_WIDTH + 10, status_text_y_start))
        
        # --- Main Status Text (moved lower) ---
        status_y_bottom = vision_processor.new_height - 100
        main_state_text = font.render(f"Mode: {traffic_system.light_state.upper()}", True, WHITE)
        screen.blit(main_state_text, (constants.RESIZE_WIDTH + 10, status_y_bottom))

        # --- Reason for State ---
        reason = "Normal Operation"
        if traffic_system.siren_heard:
            reason = "Siren Detected"
        elif traffic_system.density_alert_sent:
            reason = "High Density"
        reason_text = font.render(f"Reason: {reason}", True, WHITE)
        screen.blit(reason_text, (constants.RESIZE_WIDTH + 10, status_y_bottom + 30))
            
        pygame.display.flip()

        # Tick the system *after* drawing the current state to prepare for the next frame
        traffic_system.tick()
        frame_count += 1

    stop_audio_event.set() # Signal the audio listener to stop
    vision_processor.stop() # Gracefully stop the vision processor thread
    pygame.quit()
    print("\nProgram finished.")

if __name__ == "__main__":
    main()