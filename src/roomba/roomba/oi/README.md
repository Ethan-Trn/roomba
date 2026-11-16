# Roomba OI

`roomba.py` has a `Roomba` class for the Roomba 600 Open Interface. You call a method
and it does the serial bytes for you. It has no ROS in it.

## Setup

- Plug the Roomba's serial cable into the Pi or laptop. The port is usually `/dev/ttyUSB0`.
- The Roomba talks at 115200 baud, which is the default.
- Install `python3-serial` and add your user to `dialout`.

## Wait until the Roomba is activated

`open()` opens the port and then blocks in `wait_for_roomba()`. That function keeps
sending START and asking for a sensor packet until the Roomba answers. It prints
`Waiting for Roomba... press Clean`. **Press the Clean button on the Roomba** to wake it up.
When it answers, it prints `Roomba is awake` and your code carries on.

Use `r.open(wait=False)` to skip the wait.

## Example

```python
import time
from roomba.oi.roomba import Roomba

r = Roomba('/dev/ttyUSB0')
r.open()                    # waits until you press Clean and it wakes up
r.safe()                    # Safe mode: you can drive, it stops at cliffs

r.drive_direct(200, 200)    # left, right wheel speed in mm/s
time.sleep(1)
r.stop_moving()

print(r.sensor('voltage'))  # mV
print(r.bumpers())          # {'bump_right': False, ...}

r.beep()
r.close()
```

It also works as a context manager, which opens and closes for you:

```python
with Roomba('/dev/ttyUSB0') as r:
    r.safe()
    r.drive(200, 500)       # 200 mm/s, curve with a 500 mm radius
    time.sleep(2)
    r.stop_moving()
```

## Methods

| Group | Methods |
|---|---|
| Connection | `open()`, `wait_for_roomba()`, `close()` |
| Modes | `start()`, `safe()`, `full()`, `power()`, `reset()`, `stop()` |
| Cleaning | `clean()`, `spot()`, `dock()` |
| Driving | `drive(velocity, radius)`, `drive_direct(left, right)`, `stop_moving()` |
| Motors | `motors(main_brush, vacuum, side_brush)` |
| Lights | `leds(debris, spot, dock, check_robot, color, intensity)`, `digits('text')` |
| Sound | `song(number, notes)`, `play(number)`, `beep()` |
| Sensors | `sensor('name')`, `bumpers()` |

- **Speeds** are in mm/s, from -500 to 500. Values outside the range are clamped.
- **`drive` radius** is in mm. You can also pass `STRAIGHT`, `TURN_CW` or `TURN_CCW`
  (import them from `roomba.oi.roomba`).
- **Safe vs Full:** call `safe()` before driving. `full()` turns off the cliff and wheel-drop stops.
- **Sensor names** are the keys of `SENSORS` in `roomba.py`, for example `voltage`, `current`,
  `battery_charge`, `wall`, `cliff_left`, `oi_mode`, `left_encoder`.

## Tests

No Roomba needed:

```
cd src/roomba && python3 -m pytest test/test_roomba.py
```
