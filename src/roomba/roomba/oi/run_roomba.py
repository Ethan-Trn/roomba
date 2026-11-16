import time
from roomba.oi.roomba import Roomba

r = Roomba('/dev/ttyUSB0')
r.open()                    # waits until you press Clean and it wakes up
print(r.sensor('cliff_left'))  # mV
print(r.bumpers())          # {'bump_right': False, ...}
r.full()                    # Safe mode: you can drive, it stops at cliffs

r.drive_direct(200, 200, duration=5)   # same thing: drive 1 s (blocking), then stop
r.leds(debris=True)                 # debris LED on
r.leds(spot=True, dock=True)        # spot and dock LEDs on
r.leds(check_robot=True)            # check-robot LED on
r.leds(color=128, intensity=128)    # orange, half brightness
time.sleep(2)

r.beep()
r.close()
