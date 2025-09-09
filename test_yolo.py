from ultralytics import YOLO
import cv2
import matplotlib.pyplot as plt # Import the new library

# --- CONFIGURATION ---
MODEL_TO_USE = "yolov8n.pt"
IMAGE_TO_TEST = "test.jpg"

# --- SCRIPT ---
print("Starting the detection process...")

# 1. Load the model and image
model = YOLO(MODEL_TO_USE)
img = cv2.imread(IMAGE_TO_TEST)

if img is None:
    print(f"---!!! ERROR !!!--- Could not load the image at '{IMAGE_TO_TEST}'.")
else:
    print("Image and model loaded successfully.")
    
    # 2. Run detection
    results = model(img.copy())
    print("Detection complete.")

    # 3. Draw the boxes on the image
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = model.names[cls]
            label = f'{class_name} {conf:.2f}'
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
            
    # 4. Display the result in a pop-up window using Matplotlib
    print("Displaying result in a pop-up window...")
    
    # IMPORTANT: OpenCV reads images in BGR format, but Matplotlib displays in RGB.
    # We need to convert the color channels for it to look correct.
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    plt.figure(figsize=(10, 8)) # Optional: control the window size
    plt.imshow(img_rgb)
    plt.title("Ambulance Detection Result")
    plt.axis('off') # Hide the axes
    plt.show() # This command opens the window
    
    print("---")
    print("✅ Success! The result window has been displayed.")
    print("---")