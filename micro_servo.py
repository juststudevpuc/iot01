import requests
from gpiozero import AngularServo, Button
from signal import pause
from time import sleep

# --- CONFIGURATION ---
API_URL = "https://attcam.cc/api/devices/control_divice"
ROOM_ID = 1  # Ensure this room exists in your database

# Setup Servo (GPIO 18) and Button (GPIO 16)
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)
button = Button(16)

# State tracking
is_active = False

def sync_to_server(state):
    """Sends the hardware state to the Laravel API."""
    try:
        payload = {
            'room_id': ROOM_ID,
            'type': 'door',
            'state': state
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(API_URL, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Server Updated: door is {state}")
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Network Error: {e}")

def toggle_servo():
    global is_active
    
    if is_active:
        print("Button Pressed: Turning OFF (Moving to -90)")
        servo.angle = -90
        is_active = False
        sync_to_server('off') # Sync 'off' to attcam.cc
    else:
        print("Button Pressed: Turning ON (Moving to 90)")
        servo.angle = 90
        is_active = True
        sync_to_server('on') # Sync 'on' to attcam.cc
        
    # Small sleep to prevent accidental double-clicks (Debounce)
    sleep(0.5)

# Link the physical button to the function
button.when_pressed = toggle_servo

print("System Ready. Controlling 'door' on attcam.cc via GPIO 16/18.")
pause()