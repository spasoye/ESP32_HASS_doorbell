import network
import time
import config
import machine

def connect_wifi():
    """Connects to Wi-Fi and returns the network interface."""
    print("Connecting to "+config.SSID) 
    wlan = network.WLAN(network.STA_IF)
    time.sleep(1)
    wlan.active(True)
    time.sleep(1)
    try:
        wlan.connect(config.SSID, config.PASSWORD)
        time.sleep(1)
        while not wlan.isconnected():
            machine.idle()
    except:
        print("Error while tryin to connect")
        return "ERROR"
    finally:
        print(f'Connected! IP: {wlan.ifconfig()[0]}. Open this IP in your browser')
        return wlan

