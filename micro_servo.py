import time
import threading
import board
import adafruit_dht
from gpiozero import AngularServo, LED, Button
from mfrc522 import SimpleMFRC522  # <--- NEW LIBRARY

# --- SETTINGS ---
VALID_CARD_ID = 8473294822  # <--- 🔴 REPLACE THIS WITH YOUR ID
ROOM_ID = 1 

# --- HARDWARE SETUP ---
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)
light_led = LED(19)
door_button = Button(16)
light_button = Button(21)
reader = SimpleMFRC522() # <--- RFID READER

# Sensor
try:
    dht_device = adafruit_dht.DHT11(board.D23)
except:
    pass

# Global states
door_active = False
current_servo_angle = 0 
servo.angle = 0 # Start closed

print("System Online. Waiting for Card...")

# --- SMOOTH MOVE FUNCTION ---
def move_servo_smoothly(target_angle):
    global current_servo_angle
    step = 1 if target_angle > current_servo_angle else -1
    for angle in range(int(current_servo_angle), int(target_angle) + step, step):
        servo.angle = angle
        time.sleep(0.06) # Calm speed
    current_servo_angle = target_angle

# --- DOOR LOGIC ---
def open_door():
    global door_active
    if not door_active:
        print("🔓 Access Granted: Opening Door...")
        move_servo_smoothly(90)
        door_active = True
        
        # Auto-close after 5 seconds (Optional - remove if not needed)
        time.sleep(5)
        close_door()

def close_door():
    global door_active
    if door_active:
        print("🔒 Closing Door...")
        move_servo_smoothly(0)
        door_active = False

def access_denied():
    print("❌ Access Denied: Wrong Card!")
    # Blink Light fast 3 times to show error
    for _ in range(3):
        light_led.on()
        time.sleep(0.1)
        light_led.off()
        time.sleep(0.1)

# --- RFID BACKGROUND TASK ---
# We run RFID in a background thread so it doesn't block the buttons
def rfid_loop():
    while True:
        try:
            # Check for card (non-blocking way is harder, standard library blocks)
            # minimal delay to prevent CPU overload
            id, text = reader.read()
            
            print(f"💳 Card Detected: {id}")
            
            if id == VALID_CARD_ID:
                open_door()
            else:
                access_denied()
                
            time.sleep(1) # Prevent double reading
        except Exception as e:
            # Sometimes reading fails if card is removed too fast
            pass

# Start RFID Thread
rfid_thread = threading.Thread(target=rfid_loop, daemon=True)
rfid_thread.start()

# --- MAIN LOOP (Buttons & Sensor) ---
try:
    while True:
        # Check Button Manual Override
        if door_button.is_pressed:
            if door_active: close_door()
            else: open_door()
            time.sleep(0.5) # Debounce
            
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("Stopping...")