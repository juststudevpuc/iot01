import time
import threading
import requests
import board
# import adafruit_dht # Uncomment if you use the sensor
from gpiozero import AngularServo, Button, LED
from mfrc522 import SimpleMFRC522

# --- 1. SETTINGS ---
VALID_CARD_ID = 1047716761031 # <--- 🔴 REPLACE WITH YOUR REAL CARD ID
ROOM_ID = 1 
BASE_URL = "https://attcam.cc/api/devices"

# --- 2. HARDWARE SETUP ---
# Servo on GPIO 18
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)

# Button on Pin 36 (GPIO 16)
door_button = Button(16) 

# Light on GPIO 19 (Optional status light)
light_led = LED(19)

# RFID Reader
reader = SimpleMFRC522()

# Global Variables
door_active = False # False = Closed, True = Open
current_servo_angle = 0 
servo.angle = 0 # Start closed

print("---------------------------------------")
print("✅ System Online: RFID + Web + Button")
print("---------------------------------------")

# --- 3. HELPER FUNCTIONS ---

# Function to move the door slowly (Calm Mode)
def move_servo_smoothly(target_angle):
    global current_servo_angle
    step = 1 if target_angle > current_servo_angle else -1
    
    start = int(current_servo_angle)
    end = int(target_angle) + step
    
    for angle in range(start, end, step):
        servo.angle = angle
        time.sleep(0.06) # 0.06 = Calm speed
    current_servo_angle = target_angle

# Function to tell the Website the door status
def sync_to_web(state_str):
    url = f"{BASE_URL}/control_divice"
    payload = {"room_id": ROOM_ID, "type": "door", "state": state_str}
    try:
        requests.post(url, json=payload, timeout=2)
        print(f"📡 Sync to Web: Door -> {state_str}")
    except:
        print("⚠️ Web Sync Failed")

# --- 4. CORE DOOR LOGIC ---

# --- 4. CORE DOOR LOGIC ---

# Add this variable at the top with your other globals
auto_close_timer = None 

def open_door():
    global door_active, auto_close_timer
    if not door_active:
        print("🔓 Opening Door...")
        move_servo_smoothly(90)
        door_active = True
        sync_to_web("on")
        
        # --- NEW: Start 10-second Auto-Close Timer ---
        if auto_close_timer is not None:
            auto_close_timer.cancel() # Reset timer if it was already running
        
        auto_close_timer = threading.Timer(10.0, close_door)
        auto_close_timer.start()
        print("⏰ Auto-close timer started: 10 seconds")

def close_door():
    global door_active, auto_close_timer
    if door_active:
        # Cancel timer if door is closed manually before 10 seconds
        if auto_close_timer is not None:
            auto_close_timer.cancel()
            
        print("🔒 Closing Door...")
        move_servo_smoothly(0)
        door_active = False
        sync_to_web("off")

# Button Event (Pin 36)
door_button.when_pressed = toggle_door

# --- 5. BACKGROUND TASKS (THREADS) ---

# Task A: Check RFID Card
def rfid_loop():
    while True:
        try:
            # Check for card
            id, text = reader.read()
            print(f"💳 Card Scanned: {id}")
            
            if id == VALID_CARD_ID:
                print("✅ ID Matched!")
                toggle_door() # If open, close it. If closed, open it.
            else:
                print("❌ Access Denied!")
                # Blink light to show error
                for _ in range(3):
                    light_led.on(); time.sleep(0.1)
                    light_led.off(); time.sleep(0.1)
            
            time.sleep(2) # Wait a bit before next scan
        except Exception as e:
            pass # Ignore read errors

# Task B: Check Website Commands
def web_poll_loop():
    while True:
        try:
            url = f"{BASE_URL}/status?room_id={ROOM_ID}"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                devices = response.json().get('data', [])
                for device in devices:
                    if device['type'] == 'door':
                        # If Web says "Open" but door is "Closed" -> Open it
                        if device['state'] == 'on' and not door_active:
                            print("🌍 Web Command: OPEN")
                            open_door()
                        # If Web says "Close" but door is "Open" -> Close it
                        elif device['state'] == 'off' and door_active:
                            print("🌍 Web Command: CLOSE")
                            close_door()
        except:
            pass # Ignore connection errors
        
        time.sleep(2) # Check website every 2 seconds

# --- 6. START EVERYTHING ---

# Start RFID in background
t1 = threading.Thread(target=rfid_loop, daemon=True)
t1.start()

# Start Web Polling in background
t2 = threading.Thread(target=web_poll_loop, daemon=True)
t2.start()

# Keep main program running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping System...")