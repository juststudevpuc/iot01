from gpiozero import LED
from time import sleep

# GPIO 19 is Physical Pin 35
led = LED(19)

print("Testing LED on Pin 35 (GPIO 19)...")

while True:
    print("ON")
    led.on()
    sleep(1)
    
    print("OFF")
    led.off()
    sleep(1)