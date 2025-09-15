import cv2
import time

def check_camera(index, backend=None):
    """
    Tries to open a camera at a given index and display its feed.
    """
    backend_name = "default" if backend is None else "DSHOW"
    print(f"\n--- Checking for camera at index: {index} (Backend: {backend_name}) ---")
    
    # Attempt to open the camera
    # Use the specified backend if provided
    cap = cv2.VideoCapture(index, backend) if backend else cv2.VideoCapture(index)
    
    # Give it a moment to initialize
    time.sleep(2) 

    if not cap.isOpened():
        print(f"❌ FAILED: Could not open camera at index {index} with {backend_name} backend.")
        return

    print(f"✅ SUCCESS: Camera at index {index} opened.")
    print("Displaying feed. Press 'q' to close this window and test the next index.")

    while True:
        # Read a frame from the camera
        success, frame = cap.read()
        if not success:
            print("Error: Failed to read frame from camera.")
            break

        # Display the frame
        cv2.imshow(f"Camera Test (Index {index}) - Press 'q' to quit", frame)

        # Wait for 'q' key to be pressed to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    print("=====================================================================")
    print("This script will test your webcam with different OpenCV backends.")
    print("The 'DSHOW' backend is often more reliable on Windows.")
    print("=====================================================================")
    
    # Test index 0 with the default backend first
    check_camera(0) 
    # Now test index 0 with the DSHOW backend, which is the likely fix
    check_camera(0, cv2.CAP_DSHOW)
    print("\n--- All camera checks complete. ---")