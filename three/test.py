#!/usr/bin/env python3
"""Pi 3B+ + CP2102 check, no sensor attached.

Wiring: CP2102 in a Pi USB port. Put a jumper between the CP2102's TXD and RXD
pins (loopback). Nothing else connected.

Usage: python3 pi_check.py [port]      default /dev/ttyUSB0
Needs pyserial: sudo apt install python3-serial
"""
import subprocess
import sys


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception as e:
        return f"error: {e}"


port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"

# 1. Board identity and power history
print("Model:    ", run(["cat", "/proc/device-tree/model"]).replace("\x00", ""))
print("Throttled:", run(["vcgencmd", "get_throttled"]), "(0x0 = no undervoltage ever seen)")

# 2. Did the CP2102 enumerate? Needs USB 5V AND working USB data.
lsusb = run(["lsusb"])
cp2102 = [l for l in lsusb.splitlines() if "10c4:ea60" in l.lower()]
if not cp2102:
    sys.exit("CP2102:    NOT FOUND on USB bus -> port gives no 5V, or the "
             "CP2102/cable is bad. Try another port and check its LED.")
print("CP2102:   ", cp2102[0])

# 3. Loopback: send bytes out TX, expect them back on RX
try:
    import serial
except ImportError:
    sys.exit("pyserial missing: sudo apt install python3-serial")

msg = b"pi-cp2102-loopback-123\n"
try:
    with serial.Serial(port, 115200, timeout=1) as s:
        s.reset_input_buffer()
        s.write(msg)
        s.flush()
        echo = s.read(len(msg))
except serial.SerialException as e:
    sys.exit(f"Serial:    could not open {port}: {e}")

if echo == msg:
    print("Loopback:  PASS - USB power, USB data and CP2102 all work")
elif echo:
    print(f"Loopback:  PARTIAL - got {echo!r}, expected {msg!r}")
else:
    print("Loopback:  FAIL - nothing came back. Check the TX-RX jumper.")