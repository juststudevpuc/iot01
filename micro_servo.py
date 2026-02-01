import requests
import time
import threading
from gpiozero import AngularServo, LED, Button

# --- SETTINGS ---
BASE_URL = "https://attcam.cc/api/devices"
ROOM_ID = 1 

# --- HARDWARE SETUP ---
# Servo on GPIO 18 (Physical Pin 12)
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)

# LED on GPIO 19 (Physical Pin 35)
light_led = LED(19)

# Door Button on GPIO 16 (Physical Pin 36)
door_button = Button(16)

# Light Button on GPIO 21 (Physical Pin 40)
# Note: We use 21 because "Pin 40" is GPIO 21 in the code.
light_button = Button(21)

# Global states to track local hardware status
door_active = False
light_active = False

print("System Ready.")
print("Door Button: GPIO 16 | Light Button: GPIO 21 (Pin 40)")
print("Light LED: GPIO 19 | Servo: GPIO 18")

def sync_to_server(device_type, state_str):
    """Pushes local button changes to attcam.cc"""
    url = f"{BASE_URL}/control_divice"
    payload = {"room_id": ROOM_ID, "type": device_type, "state": state_str}
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    try:
        # We use a short timeout so the button doesn't freeze if internet is slow
        requests.post(url, json=payload, headers=headers, timeout=2)
        print(f"📡 API Sync: {device_type} is now {state_str}")
    except Exception as e:
        print(f"📡 Sync Error: {e}")

def poll_server():
    """Checks for commands coming from the website/dashboard"""
    global door_active, light_active
    url = f"{BASE_URL}/status?room_id={ROOM_ID}"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            devices = response.json().get('data', [])
            for device in devices:
                # --- SYNC LIGHT ---
                if device['type'] == 'light':
                    server_state = device['state'] # 'on' or 'off'
                    if server_state == 'on' and not light_active:
                        light_led.on()
                        light_active = True
                        print("☁️ Web turned Light ON")
                    elif server_state == 'off' and light_active:
                        light_led.off()
                        light_active = False
                        print("☁️ Web turned Light OFF")

                # --- SYNC DOOR ---
                if device['type'] == 'door':
                    server_state = device['state']
                    if server_state == 'on' and not door_active:
                        servo.angle = 90
                        door_active = True
                        print("☁️ Web OPENED Door")
                    elif server_state == 'off' and door_active:
                        servo.angle = -90
                        door_active = False
                        print("☁️ Web CLOSED Door")
    except:
        # If internet fails, just ignore it and keep running locally
        pass

def toggle_door():
    global door_active
    door_active = not door_active
    
    # Update Hardware
    if door_active:
        servo.angle = 90
        state_str = "on"
    else:
        servo.angle = -90
        state_str = "off"
        
    print(f"🔘 Door Button Pressed: {state_str}")
    sync_to_server('door', state_str)

def toggle_light():
    global light_active
    light_active = not light_active
    
    # Update Hardware
    if light_active:
        light_led.on()
        state_str = "on"
    else:
        light_led.off()
        state_str = "off"
        
    print(f"🔘 Light Button Pressed: {state_str}")
    sync_to_server('light', state_str)

# Link physical buttons to functions
door_button.when_pressed = toggle_door
light_button.when_pressed = toggle_light

def background_loop():
    while True:
        poll_server()
        time.sleep(2)

# Start Polling in the background
thread = threading.Thread(target=background_loop, daemon=True)
thread.start()

# Keep main program running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping...")