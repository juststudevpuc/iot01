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
# Servo on GPIO 18 (Pin 12)
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)

# LED on GPIO 19 (Pin 35)
light_led = LED(19)

# Door Button on GPIO 16 (Pin 36)
door_button = Button(16)

# Light Button on GPIO 21 (Pin 40)
light_button = Button(21)

# Sensor on GPIO 23 (Pin 16)
# If you have a white DHT22 sensor, change DHT11 to DHT22
try:
    dht_device = adafruit_dht.DHT11(board.D23)
except Exception as e:
    print(f"⚠️ Sensor Setup Error: {e}")

# Global states
door_active = False
light_active = False

print("System Ready.")
print("Sensors: Temp/Hum on GPIO 23")
print("Controls: Door (GPIO 16) | Light (GPIO 21)")

def sync_to_server(device_type, state_str):
    """Pushes control changes (on/off) to server"""
    url = f"{BASE_URL}/control_divice"
    payload = {"room_id": ROOM_ID, "type": device_type, "state": state_str}
    try:
        requests.post(url, json=payload, timeout=2)
        print(f"📡 Sync: {device_type} -> {state_str}")
    except:
        print(f"📡 Sync Error: Failed to update {device_type}")

def upload_sensor_data(temp, hum):
    """Pushes Temperature and Humidity to server"""
    # Note: I am guessing your API endpoint for sensors here. 
    # If you have a specific URL for sensor data, change it below!
    url = f"{BASE_URL}/control_divice" 
    
    # We send two separate requests or one depending on your API.
    # Here we send them as "devices" named 'temperature' and 'humidity'
    try:
        # Send Temperature
        payload_t = {"room_id": ROOM_ID, "type": "temperature", "state": str(temp)}
        requests.post(url, json=payload_t, timeout=2)
        
        # Send Humidity
        payload_h = {"room_id": ROOM_ID, "type": "humidity", "state": str(hum)}
        requests.post(url, json=payload_h, timeout=2)
        
        print(f"📡 Uploaded: {temp}°C | {hum}%")
    except:
        print("📡 Sensor Upload Failed")

def read_sensor():
    """Safely reads the DHT sensor"""
    try:
        t = dht_device.temperature
        h = dht_device.humidity
        if t is not None and h is not None:
            return t, h
    except RuntimeError:
        # Sensors often fail to read once in a while, it's normal
        return None, None
    return None, None

def poll_server():
    """Checks for remote commands"""
    global door_active, light_active
    url = f"{BASE_URL}/status?room_id={ROOM_ID}"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            devices = response.json().get('data', [])
            for device in devices:
                # Sync Light
                if device['type'] == 'light':
                    if device['state'] == 'on' and not light_active:
                        light_led.on(); light_active = True
                        print("☁️ Web: Light ON")
                    elif device['state'] == 'off' and light_active:
                        light_led.off(); light_active = False
                        print("☁️ Web: Light OFF")

                # Sync Door
                if device['type'] == 'door':
                    if device['state'] == 'on' and not door_active:
                        servo.angle = 90; door_active = True
                        print("☁️ Web: Door OPEN")
                    elif device['state'] == 'off' and door_active:
                        servo.angle = -90; door_active = False
                        print("☁️ Web: Door CLOSED")
    except:
        pass

def toggle_door():
    global door_active
    door_active = not door_active
    servo.angle = 90 if door_active else -90
    state = "on" if door_active else "off"
    print(f"🔘 Door Button: {state}")
    sync_to_server('door', state)

def toggle_light():
    global light_active
    light_active = not light_active
    if light_active: light_led.on()
    else: light_led.off()
    state = "on" if light_active else "off"
    print(f"🔘 Light Button: {state}")
    sync_to_server('light', state)

# Link Buttons
door_button.when_pressed = toggle_door
light_button.when_pressed = toggle_light

def background_loop():
    last_sensor_read = 0
    while True:
        # 1. Check for web commands (Every 2 seconds)
        poll_server()
        
        # 2. Read Sensor (Every 10 seconds)
        # We don't read every loop because DHT sensors are slow
        if time.time() - last_sensor_read > 10:
            temp, hum = read_sensor()
            if temp is not None:
                upload_sensor_data(temp, hum)
                last_sensor_read = time.time()
                
        time.sleep(2)

# Start Background Thread
thread = threading.Thread(target=background_loop, daemon=True)
thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping...")