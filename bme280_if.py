from bme280 import bme280
import machine
import config

def sensor_init():
    """
    Initialize the BME280 sensor.

    This function should be called once in the module's __init__ method to
    initialize the sensor. It sets up the I2C pins and creates an instance of
    the BME280 class.
    """
    global sensor
    
    print("Initializing sensor.")

    pinSDA = machine.Pin(config.SDA_pin)
    pinSCL = machine.Pin(config.SCL_pin)

    i2c = machine.SoftI2C(scl=pinSCL, sda=pinSDA)

    sensor = bme280.BME280(i2c=i2c)

def read_sensor():
    """
    Read the temperature, pressure, and humidity from the BME280 sensor.

    Returns:
        A tuple containing the temperature, pressure, and humidity in that order.
    """
    if sensor is None:
        raise ValueError("Sensor not initialized. Call sensor_init() first.")

    t, p, h = sensor.read_compensated_data()

    p = p // 256
    pi = p // 100
    pd = p - pi * 100
    hi = h // 1024
    hd = h * 100 // 1024 - hi * 100

    
    return ("{}".format(t / 100), "{}.{:02d}".format(pi, pd),
            "{}.{:02d}".format(hi, hd))
