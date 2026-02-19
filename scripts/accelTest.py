import smbus2
import time

# Create I2C bus
bus = smbus2.SMBus(1)
DEVICE_ADDRESS = 0x68

def init_mpu():
    try:
        # 1. Hard Reset the internal registers
        print("Sending Hard Reset...")
        bus.write_byte_data(DEVICE_ADDRESS, 0x6B, 0x80) 
        time.sleep(0.2) # Wait for reset
        
        # 2. Wake up (Disable Sleep Mode)
        print("Waking up sensor...")
        bus.write_byte_data(DEVICE_ADDRESS, 0x6B, 0x00)
        time.sleep(0.1)

        # 3. Read WHO_AM_I to verify
        device_id = bus.read_byte_data(DEVICE_ADDRESS, 0x75)
        print(f"✅ Connection Established! ID: {hex(device_id)}")
        return True
    except Exception as e:
        print(f"❌ Hardware Error: {e}")
        return False

if __name__ == "__main__":
    if init_mpu():
        print("Your RPi5 and HW-046 are finally shaking hands!")