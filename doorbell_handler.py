import machine
import time
import network
import umqtt.simple as mqtt
import config
import json
import ubinascii


# Define the GPIO pin for the button
button_pin = 20  
DEVICE_NAME = 'doorbell_device'
BUTTON_PIN = 0  # GPIO Pin where button is connected
MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id()).decode()

# Topics for MQTT auto-discovery
MQTT_DISCOVERY_TOPIC = f'homeassistant/sensor/{DEVICE_NAME}/config'
MQTT_BUTTON_TOPIC = f'homeassistant/{DEVICE_NAME}/button'

# Create a button object
button = machine.Pin(button_pin, machine.Pin.IN, machine.Pin.PULL_UP)

# Variable to track the last time the button was pressed
last_press_time = 0
debounce_delay = 200  # Debounce delay in milliseconds

def mqtt_discovery():   
    config_payload = {
        "name": "Button Press",
        "unique_id": f"{DEVICE_NAME}_button",
        "state_topic": MQTT_BUTTON_TOPIC,
        "value_template": "{{ value }}",
        "device": {
            "identifiers": [DEVICE_NAME],
            "name": DEVICE_NAME,
            "model": "MicroPython Button",
            "manufacturer": "Custom",
        }
    }
    
    print("Sending discovery: \n")
    mqtt_client.publish(MQTT_DISCOVERY_TOPIC, str(config_payload).replace("'", '"'))
    
    #json_payload = json.dumps(discovery_data)
    #print("Sending discovery: \n", json_payload)
    #mqtt_client.publish(discovery_topic, json_payload, retain=True)
    
# Function to run when the button is pressed
def button_pressed_callback(pin):
    global last_press_time
    current_time = time.ticks_ms()  # Get the current time in milliseconds
    
    if current_time - last_press_time > debounce_delay:
        last_press_time = current_time  # Update the last press time
        print("Button was pressed!")
        mqtt_client.publish(MQTT_BUTTON_TOPIC, "DING-DONG")

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
button.irq(trigger=machine.Pin.IRQ_FALLING, handler=button_pressed_callback)

# Main loop
try:
    while True:
        mqtt_client.check_msg()
        time.sleep(1)  # Sleep to reduce CPU usage
except KeyboardInterrupt:
    print("Program stopped")
finally:
    mqtt_client.disconnect()