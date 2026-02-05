import requests
import time
import threading
import board
import adafruit_dht
from gpiozero import AngularServo, LED, Button

# --- SETTINGS ---
BASE_URL = "https://attcam.cc/api/devices"
ROOM_ID = 1 

# --- HARDWARE SETUP ---
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)
light_led = LED(19)
door_button = Button(16)
light_button = Button(21)

# Sensor on GPIO 23
try:
    dht_device = adafruit_dht.DHT11(board.D23)
except Exception as e:
    print(f"⚠️ Sensor Error: {e}")

# Global states
door_active = False
light_active = False
current_servo_angle = 0 # Remember where the door is

# Initialize Door to Closed (0)
servo.angle = 0

print("System Online.")
print("Controls: Door(16) | Light(21)")
print("Sensor:   Temp/Hum(23)")

# --- NEW: SMOOTH MOVE FUNCTION ---
def move_servo_smoothly(target_angle):
    global current_servo_angle
    
    # Decide direction
    if target_angle > current_servo_angle:
        step = 1   # Opening
    else:
        step = -1  # Closing
        
    # Loop to move 1 degree at a time
    for angle in range(int(current_servo_angle), int(target_angle) + step, step):
        servo.angle = angle
        
        # --- CALM SPEED SETTING ---
        # 0.03 = Normal speed
        # 0.06 = Calm/Slow (Recommended)
        # 0.10 = Very Slow
        time.sleep(0.02) 
        
    current_servo_angle = target_angle

# --- API FUNCTIONS ---
def sync_control(device_type, state_str):
    url = f"{BASE_URL}/control_divice"
    payload = {"room_id": ROOM_ID, "type": device_type, "state": state_str}
    try:
        requests.post(url, json=payload, timeout=2)
        print(f"📡 Sync: {device_type} -> {state_str}")
    except:
        print(f"⚠️ Sync Failed")

def upload_sensor(temp, hum):
    url = f"{BASE_URL}/control_divice"
    try:
        requests.post(url, json={"room_id": ROOM_ID, "type": "temperature", "state": str(temp)}, timeout=2)
        requests.post(url, json={"room_id": ROOM_ID, "type": "humidity", "state": str(hum)}, timeout=2)
        print(f"☁️ Uploaded Data")
    except:
        print("⚠️ Sensor Upload Failed")

def poll_server():
    global door_active, light_active
    url = f"{BASE_URL}/status?room_id={ROOM_ID}"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            devices = response.json().get('data', [])
            for device in devices:
                # --- LIGHT CONTROL ---
                if device['type'] == 'light':
                    if device['state'] == 'on' and not light_active:
                        light_led.on(); light_active = True
                        print("📱 Web: Light ON")
                    elif device['state'] == 'off' and light_active:
                        light_led.off(); light_active = False
                        print("📱 Web: Light OFF")

                # --- DOOR CONTROL (SMOOTH) ---
                if device['type'] == 'door':
                    if device['state'] == 'on' and not door_active:
                        print("📱 Web: OPENING Door...")
                        move_servo_smoothly(90) # OPEN
                        door_active = True
                    elif device['state'] == 'off' and door_active:
                        print("📱 Web: CLOSING Door...")
                        move_servo_smoothly(0)  # CLOSE
                        door_active = False
    except:
        pass

# --- BUTTON CONTROLS ---
def toggle_door():
    global door_active
    door_active = not door_active
    
    if door_active:
        print("🔘 Button: OPENING...")
        move_servo_smoothly(90)
        state = "on"
    else:
        print("🔘 Button: CLOSING...")
        move_servo_smoothly(0)
        state = "off"
        
    sync_control('door', state)

def toggle_light():
    global light_active
    light_active = not light_active
    if light_active: light_led.on()
    else: light_led.off()
    state = "on" if light_active else "off"
    print(f"🔘 Light Button: {state}")
    sync_control('light', state)

door_button.when_pressed = toggle_door
light_button.when_pressed = toggle_light

# --- BACKGROUND LOOP ---
def background_task():
    last_sensor_time = 0
    
    while True:
        poll_server()
        
        # Sensor updates every 30s
        if time.time() - last_sensor_time > 30:
            try:
                t = dht_device.temperature
                h = dht_device.humidity
                if t is not None:
                    print(f"--------------------------------")
                    print(f"🌡️ Room Temp: {t}°C")
                    print(f"💧 Humidity:  {h}%")
                    print(f"--------------------------------")
                    upload_sensor(t, h)
                    last_sensor_time = time.time()
            except RuntimeError:
                pass
            except Exception as e:
                print(f"Sensor Error: {e}")
                
        time.sleep(2)

thread = threading.Thread(target=background_task, daemon=True)
thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping...")