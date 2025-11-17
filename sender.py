import cv2
import requests
import base64
import time

API_URL = "http://127.0.0.1:5000/video_feed" # Changed to 127.0.0.1 for local testing

cap = cv2.VideoCapture(0) 

if not cap.isOpened():
    print("Error: Could not open camera. Check index and device.")
    exit()

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        # Encode frame as JPEG buffer and then base64
        _, buffer = cv2.imencode('.jpg', frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        try:
            # Send the base64 string to the Flask API
            response = requests.post(API_URL, json={'image': jpg_as_text})
            if response.status_code != 200:
                print(f"Error sending frame: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            print("Connection Error: Could not connect to the API. Retrying...")
        
        # Limit frame rate
        time.sleep(0.05) 

except KeyboardInterrupt:
    print("Streaming stopped by user.")
finally:
    cap.release()
    cv2.destroyAllWindows()
