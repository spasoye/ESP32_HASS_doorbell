# This file is executed on every boot (including wake-boot from deepsleep)
import esp
import sys
esp.osdebug(None)
#import webrepl
#webrepl.start()
sys.path.append('/libs')
sys.path.append('/')