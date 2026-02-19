import smbus2
import time
import sys

# Constants for MPU9250
ADDR = 0x68
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H  = 0x43
PWR_MGMT_1   = 0x6B

bus = smbus2.SMBus(1)

def read_raw_data(addr):
    # Accel/Gyro data is 16-bit (two 8-bit registers)
    high = bus.read_byte_data(ADDR, addr)
    low = bus.read_byte_data(ADDR, addr + 1)
    # Combine high and low for a signed 16-bit value
    value = ((high << 8) | low)
    if value > 32768:
        value = value - 65536
    return value

def init_mpu():
    # Wake up the sensor
    bus.write_byte_data(ADDR, PWR_MGMT_1, 0)
    time.sleep(0.1)

try:
    init_mpu()
    print("✅ MPU9250 Active. Reading Accelerometer & Gyro...")
    print("-" * 50)

    while True:
        # 16384 is the sensitivity scale factor for +/- 2g (default)
        ax = read_raw_data(ACCEL_XOUT_H) / 16384.0
        ay = read_raw_data(ACCEL_XOUT_H + 2) / 16384.0
        az = read_raw_data(ACCEL_XOUT_H + 4) / 16384.0

        # 131 is the sensitivity scale factor for +/- 250 deg/s (default)
        gx = read_raw_data(GYRO_XOUT_H) / 131.0
        gy = read_raw_data(GYRO_XOUT_H + 2) / 131.0
        gz = read_raw_data(GYRO_XOUT_H + 4) / 131.0

        output = (f"ACCEL [g]: X:{ax:6.2f} Y:{ay:6.2f} Z:{az:6.2f} | "
                  f"GYRO [d/s]: X:{gx:6.2f} Y:{gy:6.2f} Z:{gz:6.2f}")
        
        sys.stdout.write(f"\r{output}")
        sys.stdout.flush()
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopped.")
except Exception as e:
    print(f"\nError: {e}")