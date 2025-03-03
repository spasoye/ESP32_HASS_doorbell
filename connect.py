import network
import time
import config

def connect_wifi():
    """Connects to Wi-Fi and returns the network interface."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(config.SSID, config.PASSWORD)
    while not wlan.isconnected():
        time.sleep(1)
    print(f'Connected! IP: {wlan.ifconfig()[0]}. Open this IP in your browser')
    return wlan

