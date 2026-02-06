import time
import threading
import requests
from gpiozero import AngularServo, Button, LED
from mfrc522 import SimpleMFRC522

# --- 1. SETTINGS ---
VALID_CARD_ID = 1047716761031 
ROOM_ID = 1 
BASE_URL = "https://attcam.cc/api/devices"

# --- 2. HARDWARE SETUP ---
# Servo: min=-90, max=90
servo = AngularServo(18, min_angle=90, max_angle=-90, min_pulse_width=0.0005, max_pulse_width=0.0025)

# Button on Pin 36 (GPIO 16)
door_button = Button(16) 

# Light on Pin 35 (GPIO 19)
light_led = LED(19)

# RFID Reader
reader = SimpleMFRC522()

# Global Variables
door_active = False 
current_servo_angle = 0 
servo.angle = 0 
auto_close_timer = None

print("---------------------------------------")
print("✅ System Online: Door + Light + RFID")
print("---------------------------------------")

# --- 3. HELPER FUNCTIONS ---

def move_servo_smoothly(target_angle):
    global current_servo_angle
    step = 1 if target_angle > current_servo_angle else -1
    start = int(current_servo_angle)
    end = int(target_angle) + step
    
    for angle in range(start, end, step):
        servo.angle = angle
        time.sleep(0.02) 
    current_servo_angle = target_angle

def sync_to_web(device_type, state_str):
    url = f"{BASE_URL}/control_divice"
    payload = {"room_id": ROOM_ID, "type": device_type, "state": state_str}
    try:
        requests.post(url, json=payload, timeout=2)
        print(f"📡 Web Updated: {device_type} -> {state_str}")
    except:
        print("⚠️ Web Sync Failed")

# --- 4. CORE DOOR LOGIC ---

def open_door():
    global door_active, auto_close_timer
    if not door_active:
        print("🔓 Opening Door...")
        move_servo_smoothly(90)
        door_active = True
        sync_to_web("door", "on")
        
        # Auto-Close Timer
        if auto_close_timer:
            auto_close_timer.cancel()
        auto_close_timer = threading.Timer(12.0, close_door)
        auto_close_timer.start()

def close_door():
    global door_active, auto_close_timer
    if door_active:
        if auto_close_timer:
            auto_close_timer.cancel()
        print("🔒 Closing Door...")
        move_servo_smoothly(0)
        door_active = False
        sync_to_web("door", "off")

def toggle_door():
    if door_active: close_door()
    else: open_door()

door_button.when_pressed = toggle_door

# --- 5. BACKGROUND THREADS ---

def rfid_loop():
    while True:
        try:
            id, text = reader.read()
            print(f"💳 Scanned: {id}")
            if id == VALID_CARD_ID:
                print("✅ Access Granted")
                toggle_door()
            else:
                print("❌ Denied")
                # Blink Light for Error
                for _ in range(3):
                    light_led.on(); time.sleep(0.1)
                    light_led.off(); time.sleep(0.1)
            time.sleep(2)
        except:
            pass

def web_poll_loop():
    while True:
        try:
            url = f"{BASE_URL}/status?room_id={ROOM_ID}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                devices = response.json().get('data', [])
                for dev in devices:
                    # DOOR Check
                    if dev['type'] == 'door':
                        if dev['state'] == 'on' and not door_active:
                            open_door()
                        elif dev['state'] == 'off' and door_active:
                            close_door()
                    
                    # LIGHT Check (Added Back)
                    elif dev['type'] == 'light':
                        if dev['state'] == 'on' and not light_led.is_lit:
                            print("💡 Web: Light ON")
                            light_led.on()
                        elif dev['state'] == 'off' and light_led.is_lit:
                            print("💡 Web: Light OFF")
                            light_led.off()
        except:
            pass
        time.sleep(2)

# --- 6. EXECUTION ---
t1 = threading.Thread(target=rfid_loop, daemon=True)
t2 = threading.Thread(target=web_poll_loop, daemon=True)
t1.start()
t2.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down...")