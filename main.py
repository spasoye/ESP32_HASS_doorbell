import machine
import time
import network
import umqtt.robust as mqtt
import json
import ubinascii
import asyncio
import micropython

import config
from connect import connect_wifi

import bme280_if
import gc


# ----- Config -----
DEVICE_IP = None
DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode()

# Topics for MQTT auto-discovery
MQTT_DISCOVERY_TOPIC = f'homeassistant/device/{DEVICE_ID}/config'

# ----- Global variables -----
# Variable to track the last time the button was pressed
last_press_time = 0
# TODO: move to config
mqtt_client = None

event_queue = []

# TODO: add IP address to discovery payload ?
# TODO: move to own module
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
            "identifiers": f'{DEVICE_ID}',  # Unique device identifier
            "name": "doorbell",          # Device name
            "manufacturer": "ESP32",   # Optional
            "model": f'{DEVICE_ID}',    # Optional
            "configuration_url": f'http://{DEVICE_IP}'
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
    if time.ticks_diff(current_time, last_press_time) > config.dbnc_delay:
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

# ----- Tasks -----
async def _button_task():
    """
    Monitors the button state and publishes a message to the MQTT broker when the button is pressed.

    This function runs in an infinite loop, checking the event queue for button press events.
    When a button press event is detected, it publishes a message to the MQTT topic defined
    by the BUTTON_TOPIC constant. The message payload is "short_press".

    The function sleeps for 100 milliseconds between checks to avoid busy-waiting.
    """
    global event_queue
    while True:
        if event_queue:
            event = event_queue.pop(0)
            if event == 'button_pressed':
                print("Button pressed!")
                mqtt_client.publish("doorbell/triggers/button1", "short_press")
        await asyncio.sleep(0.1)

async def sens_task():
    # initialize BME380
    try:
        bme280_if.sensor_init()
    except:
        raise Exception("BME280 not found. Check wiring.")

    print("Sensor initialized")

    await asyncio.sleep(2)  # wait for sensor to stabilize

    while True:
        temp, press, humd = bme280_if.read_sensor()
        print(f"Temp: {temp} °C, Humidity: {humd} %, Pressure: {press} hPa")

        mqtt_client.publish("doorbell/env_sens/temp", temp)
        mqtt_client.publish("doorbell/env_sens/humd", humd)
        mqtt_client.publish("doorbell/env_sens/press", press)
        # TODO: move to config 
        await asyncio.sleep(config.sens_t)

def main():
    global DEVICE_IP
    
    wlan = connect_wifi()
    DEVICE_IP = wlan.ifconfig()[0]  # Get the assigned IP address
    _mqtt_setup()
    
    # Publish discovery message
    _mqtt_discovery()

    # Create a button object
    button = machine.Pin(config.bell_pin , machine.Pin.IN, machine.Pin.PULL_UP)
    # Attach an interrupt to the button pin
    button.irq(trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING, handler=_button_pressed_ISR)

    loop = asyncio.get_event_loop()
    loop.create_task(_button_task())
    loop.create_task(sens_task())
    loop.create_task(_memory_cleanup())
    
    try:
        from stream_server import stream_server_start 
        loop.create_task(stream_server_start(DEVICE_IP))
    except KeyboardInterrupt:
        print("Server stopped")
    
    loop.run_forever()

    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Shuting down.")
   
   
   
   
