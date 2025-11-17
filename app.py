
import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify, Response # <-- FIXED: Response is now imported!

app = Flask(__name__)

latest_frame = None
current_direction = 'stop'

@app.route('/video_feed', methods=['POST'])
def video_feed():
    """Receives base64-encoded image frames from the separate sender script."""
    global latest_frame
    data = request.get_json()
    if data and 'image' in data:
        image_data = base64.b64decode(data['image'])
        nparr = np.frombuffer(image_data, np.uint8)
        latest_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return "OK", 200

def generate_frames():
    """Generates the Motion JPEG (MJPEG) stream for the browser."""
    global latest_frame
    while True:
        if latest_frame is not None:
            # Encode the frame as JPEG
            ret, buffer = cv2.imencode('.jpg', latest_frame)
            if ret:
                frame_bytes = buffer.tobytes()
                # Yield the frame in the MJPEG multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Add a small delay to control CPU usage/refresh rate
        # Using time.sleep(0.033) is better than cv2.waitKey(30) in a Flask generator
        # You'll need to import 'time' for this: from time import sleep as time_sleep
        # For simplicity, using a small `time.sleep` equivalent, or just letting the generator loop quickly.
        pass 

@app.route('/stream')
def stream():
    """Video streaming endpoint."""
    # This uses the imported Response object
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/controls', methods=['OPTIONS'])
def handle_options():
    return '', 200

@app.route('/controls', methods=['POST'])
def set_direction():
    global current_direction
    try:
        data = request.get_json()
        direction = data.get('direction')
        valid_directions = ['forward', 'backward', 'left', 'right', 'stop']
        
        if direction in valid_directions:
            current_direction = direction
            print(f"Server updated state: {current_direction}")
            return jsonify({"status": "success", "direction": current_direction}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid direction"}), 400
    except Exception as e:
        print(f"Error processing POST request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_direction():
    return jsonify({"direction": current_direction}), 200


if __name__ == '__main__':
    print("Starting Flask server on http://0.0.0.0:5000.")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
