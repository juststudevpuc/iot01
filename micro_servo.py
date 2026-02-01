import requests
from gpiozero import AngularServo, Button
from signal import pause
from time import sleep

# --- CONFIGURATION ---
API_URL = "https://attcam.cc/api/devices/control_divice"
ROOM_ID = 1  # Change to your actual room ID

# Servo and Button Setup
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)
button = Button(16)

is_active = False

def sync_to_server(state):
    """Sends the new state to Laravel"""
    try:
        payload = {
            'room_id': ROOM_ID,
            'type': 'door',  # Since you use a servo for the door
            'state': state
        }
        response = requests.post(API_URL, data=payload, timeout=5)
        if response.status_code == 200:
            print(f"Successfully synced '{state}' to attcam.cc")
    except Exception as e:
        print(f"Failed to sync with server: {e}")

def toggle_servo():
    global is_active
    
    if is_active:
        print("Click: Turning OFF (Moving to -90)")
        servo.angle = -90
        is_active = False
        sync_to_server('off')
    else:
        print("Click: Turning ON (Moving to 90)")
        servo.angle = 90
        is_active = True
        sync_to_server('on')
        
    sleep(0.5) # Debounce

button.when_pressed = toggle_servo

print("System Ready. Controlling 'door' on attcam.cc via Pin 16.")
pause()