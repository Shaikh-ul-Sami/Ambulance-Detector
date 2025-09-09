# ===================================================================
# ALL IMPORTS
# ===================================================================
import requests
import pygame
import cv2
import numpy as np
from ultralytics import YOLO
import tkinter as tk
from tkinter import filedialog
import threading
import queue
import sounddevice as sd
from scipy.fft import fft

# ===================================================================
# CONFIGURATION
# ===================================================================
BOT_TOKEN = "8459655122:AAHbrveXm-YJtUMA14wvBP-gEy0xABLMPjQ"
CHAT_ID = "1362872793"
PROCESS_EVERY_NTH_FRAME = 5 
RESIZE_WIDTH = 640          

# --- Audio Settings ---
SIREN_FREQUENCY_RANGE = (700, 1500) 
SIREN_LOUDNESS_THRESHOLD = 10      

siren_detected_queue = queue.Queue()

# ===================================================================
# HELPER FUNCTIONS
# ===================================================================
def send_alert(message="Siren detected! Clearing route."):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
        print("Alert sent successfully!")
    except Exception as e:
        print(f"Failed to send alert: {e}")

def choose_video_file():
    root = tk.Tk()
    root.withdraw()
    filepath = filedialog.askopenfilename(title="Select a Video File")
    return filepath

def audio_listener():
    SAMPLE_RATE = 44100
    CHUNK_SIZE = 1024
    def audio_callback(indata, frames, time, status):
        if status: print(status, flush=True)
        yf = fft(indata[:, 0])
        xf = np.fft.fftfreq(CHUNK_SIZE, 1 / SAMPLE_RATE)
        peak_index = np.argmax(np.abs(yf))
        peak_frequency = abs(xf[peak_index])
        peak_magnitude = np.abs(yf[peak_index])
        if (SIREN_FREQUENCY_RANGE[0] < peak_frequency < SIREN_FREQUENCY_RANGE[1] and 
            peak_magnitude > SIREN_LOUDNESS_THRESHOLD):
            print(f"SIREN DETECTED! (Freq: {peak_frequency:.0f} Hz, Loudness: {peak_magnitude:.0f})")
            if siren_detected_queue.empty():
                siren_detected_queue.put(True)
    print("🎤 Starting audio listener...")
    with sd.InputStream(callback=audio_callback, channels=1, samplerate=SAMPLE_RATE, blocksize=CHUNK_SIZE):
        while True:
            sd.sleep(1000)

# ===================================================================
# MAIN PROGRAM LOGIC
# ===================================================================
def main():
    listener_thread = threading.Thread(target=audio_listener, daemon=True)
    listener_thread.start()

    video_path = choose_video_file()
    if not video_path: return

    pygame.init()
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return

    frame_width, frame_height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    new_height = int(RESIZE_WIDTH * (frame_height / frame_width))
    screen = pygame.display.set_mode((RESIZE_WIDTH + 150, new_height))
    pygame.display.set_caption("Live Ambulance Detection")
    
    alert_sent, running, frame_count = False, True, 0
    siren_heard = False
    
    RED, GREEN, BLACK = (255,0,0), (0,255,0), (0,0,0)
    BOX_COLOR_DEFAULT = (255, 0, 0) # Blue
    last_results = None 

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- SIMPLIFIED LOGIC ---
        # 1. Check if a siren has been heard
        if not siren_detected_queue.empty():
            siren_heard = siren_detected_queue.get()

        # 2. If siren is heard, send the alert (only once)
        if siren_heard and not alert_sent:
            print("\n✅ SIREN CONFIRMED!")
            send_alert("🚨 Siren detected near Junction A! Clearing route now.")
            alert_sent = True

        success, frame = cap.read()
        if not success: break

        resized_frame = cv2.resize(frame, (RESIZE_WIDTH, new_height))
        
        # 3. Always run visual detection just for display
        if frame_count % PROCESS_EVERY_NTH_FRAME == 0:
            last_results = model(resized_frame, verbose=False) 
        
        # 4. Always draw the normal boxes
        if last_results:
            for r in last_results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    label = model.names[int(box.cls[0])]
                    cv2.rectangle(resized_frame, (x1, y1), (x2, y2), BOX_COLOR_DEFAULT, 2)
                    cv2.putText(resized_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, BOX_COLOR_DEFAULT, 2)

        screen.fill(BLACK)
        frame_rgb = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        frame_pygame = pygame.image.frombuffer(frame_rgb.tobytes(), frame_rgb.shape[1::-1], "RGB")
        screen.blit(frame_pygame, (0, 0))

        # 5. Traffic light is now ONLY controlled by the siren
        light_color = GREEN if siren_heard else RED
        traffic_light_x = RESIZE_WIDTH + 75
        pygame.draw.circle(screen, light_color, (traffic_light_x, 100), 40)
            
        pygame.display.flip()
        frame_count += 1

    cap.release()
    pygame.quit()
    print("\nProgram finished.")

if __name__ == "__main__":
    main()