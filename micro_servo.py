import requests
import time
import RPi.GPIO as GPIO

# Configuration
BASE_URL = "https://attcam.cc/api/devices"
CONTROL_URL = f"{BASE_URL}/control_divice"
STATUS_URL = f"{BASE_URL}/1/status"  # Room 1

# GPIO Pins
LIGHT_PIN = 17
BUTTON_PIN = 22 # Physical button for light

GPIO.setmode(GPIO.BCM)
GPIO.setup(LIGHT_PIN, GPIO.OUT)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Pull-up for button

def toggle_light_locally(channel):
    """ Triggered when physical button is pressed """
    current_state = GPIO.input(LIGHT_PIN)
    new_state = "off" if current_state == 1 else "on"
    
    # 1. Flip hardware
    GPIO.output(LIGHT_PIN, not current_state)
    
    # 2. Sync to Server
    try:
        payload = {'room_id': 1, 'type': 'light', 'state': new_state}
        requests.post(CONTROL_URL, data=payload, timeout=5)
        print(f"Button Pressed: Light synced to {new_state} on attcam.cc")
    except Exception as e:
        print("Failed to sync button press to server")

# Add Event Listener for the physical button
GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=toggle_light_locally, bouncetime=300)

def sync_from_server():
    """ Keeps hardware in sync with what users click on the website """
    try:
        response = requests.get(STATUS_URL, timeout=5)
        if response.status_code == 200:
            devices = response.json().get('data', [])
            for dev in devices:
                if dev['type'] == 'light':
                    server_state = GPIO.HIGH if dev['state'] == 'on' else GPIO.LOW
                    # Only update if the server differs from local to avoid flickering
                    if GPIO.input(LIGHT_PIN) != server_state:
                        GPIO.output(LIGHT_PIN, server_state)
    except Exception as e:
        pass

# Main Loop
try:
    print("System Running: Control via Button or attcam.cc")
    while True:
        sync_from_server()
        time.sleep(1) # Poll every second
except KeyboardInterrupt:
    GPIO.cleanup()