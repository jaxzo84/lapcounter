import serial

PORT = "COM3"  # <-- change this to your port
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)

print("Listening for lap times... (Ctrl+C to stop)")
while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print("RAW:", line)
