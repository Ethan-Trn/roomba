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

r.drive_direct(200, 200)    # left, right wheel speed in mm/s (keeps going)
time.sleep(1)
r.stop_moving()

r.drive_direct(200, 200, duration=1)   # same thing: drive 1 s (blocking), then stop

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
| Driving | `drive(velocity, radius)`, `drive_direct(left, right, duration=0)`, `stop_moving()` |
| Motors | `motors(main_brush, vacuum, side_brush)` |
| Lights | `leds(debris, spot, dock, check_robot, color, intensity)`, `digits('text')` |
| Sound | `song(number, notes)`, `play(number)`, `beep()` |
| Sensors | `sensor('name')`, `bumpers()` |

- **`drive_direct` duration:** `0` (default) sends the command and returns, so the wheels keep going until the next drive command. A value above 0 blocks for that many seconds, then stops.
- **Speeds** are in mm/s, from -500 to 500. Values outside the range are clamped.
- **`drive` radius** is in mm. You can also pass `STRAIGHT`, `TURN_CW` or `TURN_CCW`
  (import them from `roomba.oi.roomba`).
- **Safe vs Full:** call `safe()` before driving. `full()` turns off the cliff and wheel-drop stops.
- **Sensor names** are the keys of `SENSORS` in `roomba.py`, for example `voltage`, `current`,
  `battery_charge`, `wall`, `cliff_left`, `oi_mode`, `left_encoder`.

## LEDs and display

You do not turn the LEDs on first. Each `leds()` call lights what you pass it. The only
setup is putting the robot in Safe or Full mode, because it ignores LED commands in Passive mode.

```python
r.open()
r.safe()                            # required once, before any LED call
```

Then use any of these. They are **separate examples, not steps**. Pick one:

```python
r.leds(debris=True)                 # debris LED on
r.leds(spot=True, dock=True)        # spot and dock LEDs on
r.leds(check_robot=True)            # check-robot LED on

# Power button LED: color 0 = green .. 255 = red, intensity 0..255 (0 = off)
r.leds(color=0, intensity=255)      # bright green
r.leds(color=255, intensity=255)    # bright red
r.leds(color=128, intensity=128)    # orange, half brightness

r.leds()                            # all LEDs off

r.digits('HI')                      # up to 4 ASCII characters on the display
```

- **There is no blue.** The power LED is a green and red bicolor LED. The single `color` value (0..255) only blends between them: `0` is green, about `128` is orange/yellow, `255` is red. `intensity` (0..255) is brightness, and `0` turns it off.
- The debris, spot, dock and check-robot LEDs are on/off only. Their colors are fixed by the hardware.
- `leds()` sets every LED at once, so each call replaces the previous state. Pass every LED you want lit in the same call.
- There is no separate "off" command. Call `r.leds()` with the defaults to clear them all.
- `digits()` is OI opcode 164. It needs a model with a 7-segment display, and some 600-series models don't have one.

## Tests

No Roomba needed:

```
cd src/roomba && python3 -m pytest test/test_roomba.py
```
