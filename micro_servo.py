import requests
import time
import threading
from gpiozero import AngularServo, LED, Button

# --- SETTINGS ---
# Using your live URL and updated generic routes
BASE_URL = "https://attcam.cc/api/devices"
ROOM_ID = 1  # The ID of the room this Pi is physically in

# Hardware Setup
# Servo on GPIO 18, LED on GPIO 17, Button on GPIO 16
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)
light_led = LED(17)
button = Button(16)

# Global states to track hardware
door_active = False

def sync_to_server(device_type, state_str):
    """POST local hardware change to attcam.cc"""
    url = f"{BASE_URL}/control_divice"
    payload = {"room_id": ROOM_ID, "type": device_type, "state": state_str}
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    try:
        requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"📡 Synced to Web: {device_type} is {state_str}")
    except:
        print("📡 Sync Failed: Check Internet")

def poll_status_from_server():
    """GET status for this room's devices from the generic status endpoint"""
    global door_active
    url = f"{BASE_URL}/status?room_id={ROOM_ID}"
    headers = {"Accept": "application/json"}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            devices = response.json().get('data', [])
            
            for device in devices:
                # 1. Update Light
                if device['type'] == 'light':
                    if device['state'] == 'on':
                        light_led.on()
                    else:
                        light_led.off()

                # 2. Update Door (Servo)
                if device['type'] == 'door':
                    if device['state'] == 'on' and not door_active:
                        servo.angle = 90
                        door_active = True
                    elif device['state'] == 'off' and door_active:
                        servo.angle = -90
                        door_active = False
    except Exception as e:
        print(f"polling error: {e}")

def handle_physical_button():
    """Manual override: Toggles the door locally and pushes update to web"""
    global door_active
    door_active = not door_active
    
    state_str = "on" if door_active else "off"
    servo.angle = 90 if door_active else -90
    print(f"🔘 Button Pressed: Door is {state_str}")
    
    # Push to API so the website switch flips automatically
    sync_to_server('door', state_str)

# Event listener for physical button
button.when_pressed = handle_physical_button

def background_loop():
    """Runs polling in the background every 3 seconds"""
    while True:
        poll_status_from_server()
        time.sleep(3)

# Start background thread
thread = threading.Thread(target=background_loop, daemon=True)
thread.start()

print(f"🚀 Raspberry Pi Online: Monitoring Room {ROOM_ID} on attcam.cc")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")