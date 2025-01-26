import machine
import time
import network
import umqtt.simple as mqtt
import config
import json
import ubinascii

from stream_server import start_server

# ---- Doorbell button ---- 

# Define the GPIO pin for the button
button_pin = 20  
DEVICE_NAME = 'doorbell_device'
BUTTON_PIN = 0  # GPIO Pin where button is connected
MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id()).decode()

# Topics for MQTT auto-discovery
MQTT_DISCOVERY_TOPIC = f'homeassistant/sensor/{DEVICE_NAME}/config'
MQTT_BUTTON_TOPIC = f'{DEVICE_NAME}/button'

# Create a button object
button = machine.Pin(button_pin, machine.Pin.IN, machine.Pin.PULL_UP)

# Variable to track the last time the button was pressed
last_press_time = 0
debounce_delay = 50  # Debounce delay in milliseconds

def mqtt_discovery():
    discovery_payload = {
        "device": {
            "identifiers": ["0AFFD2"],  # Unique device identifier
            "name": "foobar",          # Device name
            "manufacturer": "ESP32",   # Optional
            "model": "CustomDevice"    # Optional
        },
        "o": {  # Device metadata (optional)
            "name": "foobar"
        },
        "cmps": {  # Components of the device
            "bla1": {  # Button trigger
                "p": "device_automation",
                "automation_type": "trigger",
                "payload": "short_press",
                "topic": "foobar/triggers/button1",
                "type": "button_short_press",
                "subtype": "button_1"
            },
            "bla2": {  # Environment sensor
                "p": "sensor",
                "state_topic": "foobar/sensor/sensor1",
                "unique_id": "bla_sensor001",
                "name": "Environment Sensor",
                "unit_of_measurement": "°C",
                "value_template": '{{ value_json.temperature }}'
            }
        }
    }

    # Publish the combined discovery payload
    discovery_topic = "homeassistant/device/0AFFD2/config"
    print("Payload size: ", len(json.dumps(discovery_payload)))
    print("Sending combined discovery payload:\n", bytes(json.dumps(discovery_payload),'utf-8'))
    
    mqtt_client.publish(discovery_topic, bytes(json.dumps(discovery_payload),'utf-8'))
'''
    device_info = {
        "identifiers": ["0AFFD2"],  # Unique identifier for the device
        "name": "foobar",          # Human-readable name
        "manufacturer": "ESP32",   # Optional additional info
        "model": "CustomDevice"    # Optional model information
    }

    # Discovery payload for the button trigger
    button_payload = {
        "automation_type": "trigger",
        "topic": "triggers/button1",
        "payload": "short_press",
        "type": "button_short_press",
        "subtype": "button_1",
        "device": device_info,  # Shared device information
    }

    # Discovery payload for the sensor
    sensor_payload = {
        "name": "Test Sensor",
        "state_topic": "sensor/sensor1",
        "unique_id": "bla_sensor001",
        "device": device_info,  # Shared device information
    }

    # Publish the discovery messages
    print("Sending discovery for button trigger:\n", json.dumps(button_payload))
    mqtt_client.publish("homeassistant/device_automation/foobar_button/config", json.dumps(button_payload))

    print("Sending discovery for sensor:\n", json.dumps(sensor_payload))
    mqtt_client.publish("homeassistant/sensor/foobar_sensor/config", json.dumps(sensor_payload))
    
    #json_payload = json.dumps(discovery_data)
    #print("Sending discovery: \n", json_payload)
    #mqtt_client.publish(discovery_topic, json_payload, retain=True)
'''
# Function to run when the button is pressed
def button_pressed_callback(pin):
    global last_press_time
    current_time = time.ticks_ms()  # Get the current time in milliseconds
    if pin.value() == 0:  # Falling edge (pressed)
        if current_time - last_press_time > debounce_delay:
            last_press_time = current_time  # Update the last press time
            print("Button was pressed! ")
            mqtt_client.publish(f"foobar/triggers/button1", "short_press")
    else:
        if current_time - last_press_time > debounce_delay:
            last_press_time = current_time  # Update the last press time
            print("Button released!")
            mqtt_client.publish(f"{DEVICE_NAME}/state/button", "released")
        
# Connect to Wi-Fi
def connect_wifi():
    global wlan
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

try:
    import asyncio
    wlan = connect_wifi()
    ip = wlan.ifconfig()[0]
    asyncio.run(start_server(ip, 80))
except KeyboardInterrupt:
    print("Program stopped.")
finally:
    mqtt_client.disconnect()