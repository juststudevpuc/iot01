from mfrc522 import SimpleMFRC522
reader = SimpleMFRC522()

print("💳 Place your card near the reader...")

try:
    id, text = reader.read()
    print(f"✅ Your Card ID is: {id}")
finally:
    print("Done.")