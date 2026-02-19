import time
import sys
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250

# 1. Initialize the Sensor
# We use 0x68 based on your successful i2cdetect output
mpu = MPU9250(
    address_ak=AK8963_ADDRESS,
    address_mpu_master=MPU9050_ADDRESS_68,
    bus=1,
    gfs=GFS_250,
    afs=AFS_2G,
    mfs=AK8963_BIT_16,
    mode=AK8963_MODE_C100HZ
)

print("Initializing HW-046...")
mpu.configure()

# 2. Calibration (Optional but Highly Recommended)
# This takes about 5-10 seconds. Keep the sensor perfectly still!
print("Calibrating... Keep the sensor still and level.")
mpu.calibrate() 
print("Calibration Complete!\n")

print(f"{'ACCEL (g)':^25} | {'GYRO (d/s)':^25}")
print(f"{'X':^7} {'Y':^7} {'Z':^7} | {'X':^7} {'Y':^7} {'Z':^7}")
print("-" * 55)

try:
    while True:
        # Read Master (Accel + Gyro)
        accel = mpu.readAccelerometerMaster()
        gyro = mpu.readGyroscopeMaster()

        # Format output to overwrite the same line for a "live" feel
        output = (
            f"{accel[0]:7.2f} {accel[1]:7.2f} {accel[2]:7.2f} | "
            f"{gyro[0]:7.2f} {gyro[1]:7.2f} {gyro[2]:7.2f}"
        )
        sys.stdout.write(f"\r{output}")
        sys.stdout.flush()

        time.sleep(0.05) # ~20Hz update rate

except KeyboardInterrupt:
    print("\n\nSession ended by user.")