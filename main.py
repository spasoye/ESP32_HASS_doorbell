import machine
import time
import network
import umqtt.robust as mqtt
import config
import json
import ubinascii

from stream_server import start_server

import bme280_if

# ---- Doorbell button ---- 

# Define the GPIO pin for the button
button_pin = 20

DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode()

# Topics for MQTT auto-discovery
MQTT_DISCOVERY_TOPIC = f'homeassistant/device/{DEVICE_ID}/config'


# Create a button object
button = machine.Pin(button_pin, machine.Pin.IN, machine.Pin.PULL_UP)

# initialize BME380
bme280_if.sensor_init()

# Variable to track the last time the button was pressed
last_press_time = 0
debounce_delay = 50  # Debounce delay in milliseconds

def mqtt_discovery():
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
def button_pressed_callback(pin):
    global last_press_time
    current_time = time.ticks_ms()  # Get the current time in milliseconds
    if pin.value() == 0:  # Falling edge (pressed)
        if current_time - last_press_time > debounce_delay:
            last_press_time = current_time  # Update the last press time
            print("Button was pressed! ")
            mqtt_client.publish(f"doorbell/triggers/button1", "short_press")

            # TODO do this periodicaly with timer handler
            temp, press, humd = bme280_if.read_sensor()
            
            print("Temperature: ", temp)
            print("Pressure: ", press)
            print("Humidity: ", humd)
            
            mqtt_client.publish(f"doorbell/env_sens/temp", temp)
            mqtt_client.publish(f"doorbell/env_sens/humd", humd)
            mqtt_client.publish(f"doorbell/env_sens/press", press)

        
# Connect to Wi-Fi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(config.SSID, config.PASSWORD)
    while not wlan.isconnected():
        time.sleep(1)
    print("Connected to Wi-Fi")
    return wlan


# Connect to Wi-Fi
connect_wifi()

mqtt_client = mqtt.MQTTClient(config.MQTT_CLIENT_ID, config.MQTT_BROKER, port=config.MQTT_PORT)
mqtt_client.connect()

# Publish discovery message
mqtt_discovery()

# Attach an interrupt to the button pin
button.irq(trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING, handler=button_pressed_callback)

bme280_if.sensor_init()

try:
    import asyncio
    wlan = connect_wifi()
    ip = wlan.ifconfig()[0]
    asyncio.run(start_server(ip, 80))
except KeyboardInterrupt:
    print("Program stopped.")
finally:
    mqtt_client.disconnect()