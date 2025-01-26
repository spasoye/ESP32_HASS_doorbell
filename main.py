import machine
import time
import network
import umqtt.simple as mqtt
import config
import json
import ubinascii

import asyncio
from camera import Camera, FrameSize, PixelFormat

cam = Camera(frame_size=FrameSize.VGA, pixel_format=PixelFormat.JPEG, jpeg_quality=85, init=False)

# ---- Camera stream  ---- 
async def stream_camera(writer):
    try:
        cam.init()
        if not cam.get_bmp_out() and cam.get_pixel_format() != PixelFormat.JPEG:
            cam.set_bmp_out(True)

        writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n')
        await writer.drain()

        while True:
            frame = cam.capture()
            if frame:
                if cam.get_pixel_format() == PixelFormat.JPEG:
                    writer.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n')
                else:
                    writer.write(b'--frame\r\nContent-Type: image/bmp\r\n\r\n')
                writer.write(frame)
                await writer.drain()
                
    finally:
        cam.deinit()
        writer.close()
        await writer.wait_closed()
        print("Streaming stopped and camera deinitialized.")

async def handle_client(reader, writer):
    try:
        request = await reader.read(1024)
        request = request.decode()

        if 'GET /stream' in request:
            print("Start streaming...")
            await stream_camera(writer)

        elif 'GET /set_' in request:
            method_name = request.split('GET /set_')[1].split('?')[0]
            value = int(request.split('value=')[1].split(' ')[0])
            set_method = getattr(cam, f'set_{method_name}', None)
            if callable(set_method):
                print(f"setting {method_name} to {value}")
                set_method(value)
                response = 'HTTP/1.1 200 OK\r\n\r\n'
                writer.write(response.encode())
                await writer.drain()
            else:
                response = 'HTTP/1.1 404 Not Found\r\n\r\n'
                writer.write(response.encode())
                await writer.drain()

        elif 'GET /get_' in request:
            method_name = request.split('GET /get_')[1].split(' ')[0]
            get_method = getattr(cam, f'get_{method_name}', None)
            if callable(get_method):
                value = get_method()
                print(f"{method_name} is {value}")
                response = f'HTTP/1.1 200 OK\r\n\r\n{value}'
                writer.write(response.encode())
                await writer.drain()
            else:
                response = 'HTTP/1.1 404 Not Found\r\n\r\n'
                writer.write(response.encode())
                await writer.drain()

        else:
            writer.write('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'.encode() + html.encode())
            await writer.drain()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def start_server():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 80)
    print(f'Server is running on {wlan.ifconfig()[0]}:80')
    while True:
        await asyncio.sleep(3600)
        
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


# Connect to Wi-Fi
connect_wifi()

mqtt_client = mqtt.MQTTClient(config.MQTT_CLIENT_ID, config.MQTT_BROKER, port=config.MQTT_PORT)
mqtt_client.connect()

# Publish discovery message
mqtt_discovery()

# Attach an interrupt to the button pin
button.irq(trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING, handler=button_pressed_callback)

try:
    with open("CameraSettings.html", 'r') as file:
        html = file.read()
except Exception as e:
    print("Error reading CameraSettings.html file. You might forgot to copy it from the examples folder.")
    raise e

# Main loop
try:
    while True:
        asyncio.run(start_server())
        mqtt_client.check_msg()
        time.sleep(1)  # Sleep to reduce CPU usage
except KeyboardInterrupt:
    print("Program stopped")
    cam.deinit()
finally:
    mqtt_client.disconnect()