import machine
import time
import network
import umqtt.simple as mqtt
import config
import json


# Define the GPIO pin for the button
button_pin = 20
DEVICE_NAME = 'doorbell'
MQTT_DISCOVERY_TOPIC = f'homeassistant/device/{DEVICE_NAME}/config'
MQTT_BUTTON_TOPIC = f'{DEVICE_NAME}/button'

# Create a button object
button = machine.Pin(button_pin, machine.Pin.IN, machine.Pin.PULL_UP)

# Variable to track the last time the button was pressed
last_press_time = 0
debounce_delay = 200  # Debounce delay in milliseconds

def mqtt_discovery():
    discovery_payload = {
        "dev": {
            "ids": [DEVICE_NAME],  # Unique identifier for the device
            "name": "Doorbell Button",  # Friendly name in Home Assistant
            "mf": "Custom",  # Manufacturer
            "mdl": "DIY",  # Model
            "sw": "1.0",  # Software version
            "sn": "TODO",  # Serial number
            "hw": "1.0",  # Hardware revision
        },
        "o": {
            "name": "Button Controller",
        },
        "cmps": {
            "button_sensor": {
                "platform": "button",
                "type": "binary_sensor",  # Type of entity (binary_sensor in this case)
                "device_class": "null",  # Optional: Button press typically triggers presence-like behavior
                "unique_id": f"{DEVICE_NAME}_button",  # Unique entity identifier
                "state_topic": "button",  # Topic for button state
                "state_class": "measurement",
                "val_tpl": "{{ value_json.state }}",
                "payload_press": "PRESS",  # State value indicating the button was pressed
                #"payload_off": "released",  # Optional: A state when button was released
            },
        },
        "state_topic": f"{DEVICE_NAME}/state",
        #"avty_t": f"{DEVICE_NAME}/availability",
        #"pl_avail": "online",
        #"pl_not_avail": "offline",
    }
    
    json_payload = json.dumps(discovery_payload)
    mqtt_client.publish(MQTT_DISCOVERY_TOPIC, json_payload)
    print("MQTT Discovery payload sent.")   
    
# Function to run when the button is pressed
def button_pressed_callback(pin):
    global last_press_time
    current_time = time.ticks_ms()  # Get the current time in milliseconds
    if pin.value() == 0:  # Falling edge (pressed)
        if current_time - last_press_time > debounce_delay:
            last_press_time = current_time  # Update the last press time
            print("Button was pressed!")
            mqtt_client.publish(f"{DEVICE_NAME}/state/button", "PRESS")
    else:
        if current_time - last_press_time > debounce_delay:
            last_press_time = current_time  # Update the last press time
            print("Button released!")
            mqtt_client.publish(f"{DEVICE_NAME}/state/button", "released")
        
# Connect to Wi-Fi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(config.SSID, config.PASSWORD)
    while not wlan.isconnected():
        time.sleep(1)
    print("Connected to Wi-Fi")


# Connect to Wi-Fi
connect_wifi()

mqtt_client = mqtt.MQTTClient(config.MQTT_CLIENT_ID, config.MQTT_BROKER, port=config.MQTT_PORT)
mqtt_client.connect()

# Publish discovery message
mqtt_discovery()

# Attach an interrupt to the button pin
button.irq(trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING, handler=button_pressed_callback)

# Main loop
try:
    while True:
        mqtt_client.check_msg()
        time.sleep(1)  # Sleep to reduce CPU usage
except KeyboardInterrupt:
    print("Program stopped")
finally:
    mqtt_client.disconnect()