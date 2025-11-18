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


from PCA9685 import PCA9685

# --------------------  SETTINGS  --------------------
# The four commands the Mac can send us
VALID_COMMANDS = ['forward', 'backward', 'right', 'left']

# How fast the motors spin (0-100 %)
DEFAULT_SPEED = 100

# Where the Mac’s Flask server is listening
API_URL = "http://192.168.240.3:5000/status"

# --------------------  MOTOR DRIVER  --------------------
class MotorDriver:
    """
    Tiny wrapper around the PCA9685 PWM board so we can say
    “left wheel forward”, “right wheel stop”, etc. without
    remembering which pin is which every time.
    """

    def __init__(self):
        # PCA9685 channel numbers (these never change)
        self.PWMA = 0   # left  speed
        self.AIN1 = 1   # left  dir 1
        self.AIN2 = 2   # left  dir 2

        self.PWMB = 5   # right speed
        self.BIN1 = 3   # right dir 1
        self.BIN2 = 4   # right dir 2

        # fire up the board
        self.pwm = PCA9685(0x40, debug=False)
        self.pwm.setPWMFreq(50)

    # --------  left/right, forward/back  --------
    def MotorRun(self, motor_id: int, direction: str, speed: int):
        """
        Spin one wheel.

        motor_id : 0 = left wheel, 1 = right wheel
        direction: 'forward' or 'backward'
        speed    : 0 – 100 (duty-cycle %)
        returns  : nothing (just moves the motor)
        """
        if speed > 100:
            return

        # pick the correct PWM channel
        pwm_pin = self.PWMA if motor_id == 0 else self.PWMB
        self.pwm.setDutycycle(pwm_pin, speed)

        # set the two direction pins
        if motor_id == 0:          # LEFT
            if direction == 'forward':
                self.pwm.setLevel(self.AIN1, 0)
                self.pwm.setLevel(self.AIN2, 1)
            else:                  # backward
                self.pwm.setLevel(self.AIN1, 1)
                self.pwm.setLevel(self.AIN2, 0)
        else:                      # RIGHT
            if direction == 'forward':
                self.pwm.setLevel(self.BIN1, 1)
                self.pwm.setLevel(self.BIN2, 0)
            else:                  # backward
                self.pwm.setLevel(self.BIN1, 0)
                self.pwm.setLevel(self.BIN2, 1)

    # --------  emergency stop  --------
    def MotorStop(self, motor_id: int):
        """
        Immediately stop one wheel by setting its duty-cycle to zero.
        motor_id : 0 = left, 1 = right
        returns  : nothing
        """
        pwm_pin = self.PWMA if motor_id == 0 else self.PWMB
        self.pwm.setDutycycle(pwm_pin, 0)

# --------------------  COMMAND DISPATCHER  --------------------
def execute_command(cmd: str):
    """
    Turn the string that came from the Mac into real wheel motion.

    cmd : 'forward' | 'backward' | 'left' | 'right' | 'stop' | anything else
    returns: nothing (just moves or stops motors)
    """
    if cmd == 'forward':
        Motor.MotorRun(0, 'forward', DEFAULT_SPEED)
        Motor.MotorRun(1, 'forward', DEFAULT_SPEED)

    elif cmd == 'backward':
        Motor.MotorRun(0, 'backward', DEFAULT_SPEED)
        Motor.MotorRun(1, 'backward', DEFAULT_SPEED)

    elif cmd == 'left':          # pivot left
        Motor.MotorRun(0, 'backward', DEFAULT_SPEED)
        Motor.MotorRun(1, 'forward',  DEFAULT_SPEED)

    elif cmd == 'right':         # pivot right
        Motor.MotorRun(0, 'forward',  DEFAULT_SPEED)
        Motor.MotorRun(1, 'backward', DEFAULT_SPEED)

    elif cmd == 'stop':
        Motor.MotorStop(0)
        Motor.MotorStop(1)

    else:                        # unknown command – play safe
        Motor.MotorStop(0)
        Motor.MotorStop(1)

# --------------------  MAIN LOOP  --------------------
Motor = MotorDriver()
last_command = 'stop'          # remember what we did last time

print("Pi motor client alive – polling the Mac every 100 ms…")

while True:
    try:
        # ask the Mac for the latest order
        reply = requests.get(API_URL, timeout=1)
        reply.raise_for_status()
        new_cmd = reply.json().get('direction', 'stop')

        # only touch the motors if the order actually changed
        if new_cmd != last_command:
            print(f"new order → {new_cmd}")
            execute_command(new_cmd)
            last_command = new_cmd

    # ----  network hiccups ----
    except requests.exceptions.ConnectionError:
        if last_command != 'error':
            print("Mac unreachable – stopping motors")
            execute_command('stop')
            last_command = 'error'

    except requests.exceptions.Timeout:
        if last_command != 'timeout':
            print("Mac too slow – stopping motors")
            execute_command('stop')
            last_command = 'timeout'

    # ----  anything else ----
    except Exception as e:
        print(f"Unexpected glitch: {e} – stopping motors")
        execute_command('stop')
        last_command = 'error'

    time.sleep(0.1)   
