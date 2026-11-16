import time
from roomba.oi.roomba import Roomba

r = Roomba('/dev/ttyUSB0')
r.open()                    # waits until you press Clean and it wakes up
r.safe()                    # Safe mode: you can drive, it stops at cliffs

r.drive_direct(200, 200, duration=1)   # same thing: drive 1 s (blocking), then stop

print(r.sensor('cliff_left'))  # mV
print(r.bumpers())          # {'bump_right': False, ...}

r.beep()
r.close()
