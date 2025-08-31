import machine
import time
import network
import umqtt.robust as mqtt
import json
import ubinascii
import asyncio

import config
from connect import connect_wifi
from stream_server import start_server

import bme280_if
import gc

# ---- Doorbell button ---- 

# Define the GPIO pin for the button
button_pin = 20

DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode()

# Topics for MQTT auto-discovery
MQTT_DISCOVERY_TOPIC = f'homeassistant/device/{DEVICE_ID}/config'

# Variable to track the last time the button was pressed
last_press_time = 0
debounce_delay = 50  # Debounce delay in milliseconds

mqtt_client = None

def _mqtt_discovery():
    
    """
    Publishes a combined discovery payload for all components of the doorbell device to the MQTT broker.

    This function is called once at startup and is responsible for publishing the configuration of the device to the MQTT broker.

    The payload is JSON encoded and contains the following information:
    - Device metadata (optional)
    - Components of the device (e.g. button, environment sensors)

    The payload is published to the topic defined by the MQTT_DISCOVERY_TOPIC constant.
    """

    discovery_payload = {
        "device": {
            "identifiers": ["0AFFD2"],  # Unique device identifier
            "name": "doorbell",          # Device name
            "manufacturer": "ESP32",   # Optional
            "model": "CustomDevice"    # Optional
        },
        "o": {  # Device metadata (optional)
            "name": "doorbell"
        },
        "cmps": {  # Components of the device
            "button": {  # Button trigger
                "p": "device_automation",
                "automation_type": "trigger",
                "payload": "short_press",
                "topic": "doorbell/triggers/button1",
                "type": "button_short_press",
                "subtype": "button_1"
            },
            "temp": {  # Environment sensor
                "p": "sensor",
                "state_topic": "doorbell/env_sens/temp",
                "unique_id": "doorbell_temp",
                "name": "Doorbell temperature",
                "unit_of_measurement": "°C",
                "value_template": '{{ value }}'
            },
            "humd": {  # Environment sensor
                "p": "sensor",
                "state_topic": "doorbell/env_sens/humd",
                "unique_id": "doorbell_hum",
                "name": "Doorbell humidity",
                "unit_of_measurement": "%",
                "value_template": '{{ value }}'
            },
            "press": {  # Environment sensor
                "p": "sensor",
                "state_topic": "doorbell/env_sens/press",
                "unique_id": "doorbell_press",
                "name": "Doorbell pressure",
                "unit_of_measurement": "hPa",
                "value_template": '{{ value }}'
            }
        }
    }

    # Publish the combined discovery payload
    print("Payload size: ", len(json.dumps(discovery_payload)))
    print("Sending combined discovery payload:\n", bytes(json.dumps(discovery_payload),'utf-8'))
    
    mqtt_client.publish(MQTT_DISCOVERY_TOPIC, bytes(json.dumps(discovery_payload),'utf-8'))

# Function to run when the button is pressed
def _button_pressed_ISR(pin):
    global last_press_time
    current_time = time.ticks_ms()  # Get the current time in milliseconds
    if time.ticks_diff(current_time, last_press_time) > debounce_delay:
        micropython.schedule(_button_pressed_callback, 0)
    last_press_time = current_time

def _button_pressed_callback(_): 
    event_queue.append('button_pressed')       
        
# Connect to Wi-Fi
def _connect_wifi():
    """
    Connects to a Wi-Fi network using the configured SSID and password.

    Activates the WLAN interface in station mode and attempts to connect 
    to the specified Wi-Fi network. Waits until the connection is established 
    before returning the WLAN object.

    Returns:
        WLAN: The WLAN object after a successful connection.
    """

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(config.SSID, config.PASSWORD)
    while not wlan.isconnected():
        time.sleep(1)
    print("Connected to Wi-Fi")
    return wlan

async def _memory_cleanup() -> None:
    """
    Runs a periodic garbage collection to free up memory.

    This is necessary because the camera module allocates memory for the frames
    and does not release it back to the system. This can lead to a memory leak
    over time. The garbage collector is run every 5 minutes to clean up unused
    memory.
    """
    while True:
        print("Memory cleanup.")
        gc.collect()
        await asyncio.sleep(100)

def _mqtt_setup():
    global mqtt_client
    mqtt_client = mqtt.MQTTClient(config.MQTT_CLIENT_ID, config.MQTT_BROKER, port=config.MQTT_PORT)
    mqtt_client.connect()
    print("MQTT client connected")

def main():
    wlan = connect_wifi()
    ip = wlan.ifconfig()[0]  # Get the assigned IP address

    # Create a button object
    button = machine.Pin(button_pin, machine.Pin.IN, machine.Pin.PULL_UP)
    # Attach an interrupt to the button pin
    button.irq(trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING, handler=_button_pressed_callback)

    # initialize BME380
    bme280_if.sensor_init()

    _mqtt_setup()
    
    # Publish discovery message
    _mqtt_discovery()

    try:
        asyncio.run(start_server(ip))
    except KeyboardInterrupt:
        print("Server stopped")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Shuting down.")
   
