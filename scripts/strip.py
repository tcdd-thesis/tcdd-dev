import smbus2
import time

# Basic check using the low-level smbus2 library
bus = smbus2.SMBus(1)
address = 0x68

try:
    # Try to read the "Who Am I" register (0x75)
    # The MPU-9250 should respond with 0x71 or 0x73
    device_id = bus.read_byte_data(address, 0x75)
    print(f"Connection Successful! Device ID: {hex(device_id)}")
    
    # Wake up the sensor (write 0 to Power Management 1)
    bus.write_byte_data(address, 0x6B, 0x00)
    print("Sensor Woken Up.")

except Exception as e:
    print(f"Failed to connect: {e}")