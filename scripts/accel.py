import time
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250

# Initialize the MPU9250
# Note: GFS (Gyro Full Scale), AFS (Accel Full Scale)
mpu = MPU9250(
    address_ak=AK8963_ADDRESS,
    address_mpu_master=MPU9050_ADDRESS_68, # Default I2C address
    bus=1,
    gfs=GFS_250, 
    afs=AFS_2G, 
    mfs=AK8963_BIT_16, 
    mode=AK8963_MODE_C100HZ
)

# Configure the sensor with the settings above
mpu.configure()

print("| {:^10} | {:^10} | {:^10} |".format("X", "Y", "Z"))
print("-" * 40)

try:
    while True:
        # Read Accelerometer data
        # Returns a list: [x, y, z]
        accel_data = mpu.readAccelerometerMaster()
        
        x = accel_data[0]
        y = accel_data[1]
        z = accel_data[2]

        # Print formatted data
        print(f"| {x:10.4f} | {y:10.4f} | {z:10.4f} |", end="\r")
        
        time.sleep(0.1) # 10Hz refresh rate

except KeyboardInterrupt:
    print("\n\nStopped by user.")