import cv2

# Define the path to your image
image_path = "test.jpg"

print(f"Attempting to load image from: {image_path}")

# Load the image using OpenCV
img = cv2.imread(image_path)

# Check if the image was loaded successfully
if img is None:
    print("---!!! ERROR !!!---")
    print("The image could not be loaded. Please check that:")
    print("1. The file 'test.jpg' is in the same folder as this script.")
    print("2. The filename is spelled correctly.")
else:
    print("Image loaded successfully!")
    print("Displaying the image now. Press any key to close the window.")
    
    # Display the loaded image
    cv2.imshow("OpenCV Sanity Check", img)
    
    # Wait for a key press to close the image window
    cv2.waitKey(0)
    
    # Clean up
    cv2.destroyAllWindows()