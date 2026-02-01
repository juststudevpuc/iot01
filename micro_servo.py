import requests
import time
import threading
from gpiozero import AngularServo, LED, Button

# --- SETTINGS ---
BASE_URL = "https://attcam.cc/api/devices"
ROOM_ID = 1 

# Hardware Setup
# Servo on GPIO 18, LED on GPIO 17
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)
light_led = LED(17)

# Buttons: Pin 16 for Door, Pin 20 for Light
door_button = Button(16)
light_button = Button(20)

# Global states to track local hardware status
door_active = False
light_active = False

def sync_to_server(device_type, state_str):
    """Pushes local button changes to attcam.cc"""
    url = f"{BASE_URL}/control_divice"
    payload = {"room_id": ROOM_ID, "type": device_type, "state": state_str}
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    try:
        requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"📡 API Sync: {device_type} is now {state_str}")
    except:
        print("📡 Sync Error: Check internet connection")

def poll_server():
    """Checks for commands coming from the website/dashboard"""
    global door_active, light_active
    url = f"{BASE_URL}/status?room_id={ROOM_ID}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            devices = response.json().get('data', [])
            for device in devices:
                # Sync Light from Web
                if device['type'] == 'light':
                    if device['state'] == 'on':
                        light_led.on()
                        light_active = True
                    else:
                        light_led.off()
                        light_active = False

                # Sync Door from Web
                if device['type'] == 'door':
                    if device['state'] == 'on' and not door_active:
                        servo.angle = 90
                        door_active = True
                    elif device['state'] == 'off' and door_active:
                        servo.angle = -90
                        door_active = False
    except:
        pass

def toggle_door():
    global door_active
    door_active = not door_active
    state_str = "on" if door_active else "off"
    servo.angle = 90 if door_active else -90
    print(f"🔘 Door Button: {state_str}")
    sync_to_server('door', state_str)

def toggle_light():
    global light_active
    light_active = not light_active
    state_str = "on" if light_active else "off"
    if light_active:
        light_led.on()
    else:
        light_led.off()
    print(f"🔘 Light Button: {state_str}")
    sync_to_server('light', state_str)

# Link physical buttons to functions
door_button.when_pressed = toggle_door
light_button.when_pressed = toggle_light

def background_loop():
    while True:
        poll_server()
        time.sleep(3)

# Start Polling
thread = threading.Thread(target=background_loop, daemon=True)
thread.start()

print(f"🚀 System Online: Room {ROOM_ID} | Door (Pin 16) | Light (Pin 20)")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping...")