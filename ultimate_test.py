from PIL import Image
import numpy as np
import cv2

# We will use the same 'test.jpg' file
image_path = "test.jpg"
print(f"Attempting to load '{image_path}' using the Pillow library...")

try:
    # 1. Open the image using Pillow (PIL)
    pil_image = Image.open(image_path)
    print("Image loaded successfully with Pillow.")

    # 2. Convert the Pillow image to a format OpenCV can use (NumPy array)
    # Pillow opens images in RGB format, so we convert it to BGR for OpenCV
    opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    print("Image converted for OpenCV.")

    # 3. Display the image using OpenCV
    cv2.imshow("Ultimate Test with Pillow", opencv_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    print("Test finished.")

except FileNotFoundError:
    print(f"---!!! ERROR !!!--- Could not find the file at '{image_path}'")
except Exception as e:
    print(f"An unexpected error occurred: {e}")