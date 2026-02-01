import requests
import time
import threading
from gpiozero import AngularServo, Button

# --- CONFIGURATION ---
BASE_URL = "https://attcam.cc/api/devices"
ROOM_ID = 1

# Hardware Setup
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)
button = Button(16)

# Global state to prevent unnecessary updates
is_active = False

def push_to_server(state_str):
    """Sends local button state to attcam.cc"""
    url = f"{BASE_URL}/control_divice"
    payload = {"room_id": ROOM_ID, "type": "door", "state": state_str}
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    try:
        requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"✅ Pushed to Server: {state_str}")
    except Exception as e:
        print(f"❌ Push Error: {e}")

def check_server_status():
    """Reads status from attcam.cc/api/devices/1/status"""
    global is_active
    url = f"{BASE_URL}/{ROOM_ID}/status"
    headers = {"Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json().get('data', [])
            # Find the 'door' device in the list
            for device in data:
                if device['type'] == 'door':
                    server_state = device['state']
                    
                    # If the server is different from local, update hardware
                    if server_state == 'on' and not is_active:
                        print("🌐 Web Command: Turning ON")
                        servo.angle = 90
                        is_active = True
                    elif server_state == 'off' and is_active:
                        print("🌐 Web Command: Turning OFF")
                        servo.angle = -90
                        is_active = False
    except Exception as e:
        print(f"❌ Polling Error: {e}")

def handle_button_press():
    """Toggles hardware locally and pushes to server"""
    global is_active
    is_active = not is_active
    
    state_str = "on" if is_active else "off"
    servo.angle = 90 if is_active else -90
    print(f"🔘 Button Pressed: {state_str}")
    
    # Push this change to the API immediately
    push_to_server(state_str)

# Link the physical button
button.when_pressed = handle_button_press

def polling_loop():
    """Background loop to check server every 3 seconds"""
    while True:
        check_server_status()
        time.sleep(3)

# Start Polling in a background thread
poll_thread = threading.Thread(target=polling_loop, daemon=True)
poll_thread.start()

print("🚀 System Online at attcam.cc")
print("Listening for button presses and web commands...")

# Keep main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping system...")