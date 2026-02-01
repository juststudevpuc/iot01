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
# Servo on GPIO 18
servo = AngularServo(18, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025)

# LED on GPIO 19
light_led = LED(19)

# Door Button on GPIO 16
door_button = Button(16)

# Light Button on GPIO 21 (Pin 40)
light_button = Button(21)

# Sensor on GPIO 23 (Pin 16)
# Note: If using white DHT22, change DHT11 to DHT22 below
try:
    dht_device = adafruit_dht.DHT11(board.D23)
except Exception as e:
    print(f"⚠️ Sensor Error: {e}")

# Global states
door_active = False
light_active = False

print("System Online.")
print("controls: Door(16) | Light(21)")
print("Sensor:   Temp/Hum(23)")

# --- API FUNCTIONS ---
def sync_control(device_type, state_str):
    """Updates the server when you click a physical button"""
    url = f"{BASE_URL}/control_divice"
    payload = {"room_id": ROOM_ID, "type": device_type, "state": state_str}
    try:
        requests.post(url, json=payload, timeout=2)
        print(f"📡 Sync: {device_type} is now {state_str}")
    except:
        print(f"⚠️ Sync Failed (Internet?)")

def upload_sensor(temp, hum):
    """Uploads Temperature and Humidity to the server"""
    url = f"{BASE_URL}/control_divice"
    try:
        # Send Temperature
        payload_t = {"room_id": ROOM_ID, "type": "temperature", "state": str(temp)}
        requests.post(url, json=payload_t, timeout=2)
        
        # Send Humidity
        payload_h = {"room_id": ROOM_ID, "type": "humidity", "state": str(hum)}
        requests.post(url, json=payload_h, timeout=2)
        
        print(f"☁️ Uploaded: {temp}°C | {hum}%")
    except:
        print("⚠️ Sensor Upload Failed")

def poll_server():
    """Checks website for remote commands"""
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
                        print("📱 Web turned Light ON")
                    elif device['state'] == 'off' and light_active:
                        light_led.off(); light_active = False
                        print("📱 Web turned Light OFF")

                # Sync Door
                if device['type'] == 'door':
                    if device['state'] == 'on' and not door_active:
                        servo.angle = 90; door_active = True
                        print("📱 Web OPENED Door")
                    elif device['state'] == 'off' and door_active:
                        servo.angle = -90; door_active = False
                        print("📱 Web CLOSED Door")
    except:
        pass

# --- BUTTON FUNCTIONS ---
def toggle_door():
    global door_active
    door_active = not door_active
    servo.angle = 90 if door_active else -90
    state = "on" if door_active else "off"
    print(f"🔘 Door Button: {state}")
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
        # 1. Check Web Commands (Every 2 seconds)
        poll_server()
        
        # 2. Read Sensor (Every 10 seconds)
        # We wait 10s because DHT sensors are slow and can crash if read too fast
        if time.time() - last_sensor_time > 10:
            try:
                t = dht_device.temperature
                h = dht_device.humidity
                if t is not None:
                    print(f"🌡️ Room Temp: {t}°C") # Print to screen as requested
                    upload_sensor(t, h)
                    last_sensor_time = time.time()
            except RuntimeError:
                # Sensor reading failed this time (normal), just skip
                pass
            except Exception as e:
                print(f"Sensor Error: {e}")
                
        time.sleep(2)

# Start the background thread
thread = threading.Thread(target=background_task, daemon=True)
thread.start()

# Keep main program alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping...")