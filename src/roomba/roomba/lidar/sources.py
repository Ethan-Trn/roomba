"""Where lidar bytes come from. Subclass LidarSource and override the three methods.

Everything after the bytes (packets, CRC, scans) lives in ld06.py and is the same
for every source. Only "how do I get bytes" changes.
"""
import glob
import math
import time
from abc import ABC, abstractmethod

from roomba.lidar import ld06


class LidarSource(ABC):
    """Base class: open it, read() raw bytes (never blocks), close it."""

    @abstractmethod
    def open(self):
        """Start the source. Raise on failure."""

    @abstractmethod
    def read(self):
        """Return whatever bytes are available right now (possibly b'')."""

    @abstractmethod
    def close(self):
        """Release the source."""

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()


class SerialSource(LidarSource):
    """Any serial port at the LD06's 230400 8N1. UART and USB build on this."""

    BAUD = 230400
    DEFAULT_PORT = ''

    def __init__(self, port=None, baud=None):
        self.port = port or self.DEFAULT_PORT
        self.baud = baud or self.BAUD
        self._ser = None

    def resolve_port(self):
        """Return the device path to open. Subclasses may override."""
        return self.port

    def open(self):
        import serial  # imported here so tests and the sim do not need pyserial
        self._ser = serial.Serial(self.resolve_port(), self.baud, timeout=0)

    def read(self):
        n = self._ser.in_waiting
        return self._ser.read(n) if n else b''

    def close(self):
        if self._ser is not None:
            self._ser.close()
            self._ser = None


class UartSource(SerialSource):
    """The Pi's GPIO UART (pins 8/10). Needs dtoverlay=disable-bt for a clean 230400."""

    DEFAULT_PORT = '/dev/serial0'


class UsbSource(SerialSource):
    """The USB serial adapter. Picks the first /dev/ttyUSB* or /dev/ttyACM* if no port is given."""

    def resolve_port(self):
        if self.port:
            return self.port
        found = sorted(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))
        if not found:
            raise FileNotFoundError('no /dev/ttyUSB* or /dev/ttyACM* found, is the lidar plugged in?')
        return found[0]


class SimulatedSource(LidarSource):
    """Fake LD06: a 4 m x 3 m room with a pillar, at the real packet rate."""

    SPEED_DPS = 3600
    STEP_DEG = SPEED_DPS / ld06.POINT_RATE  # 0.8 degrees between points

    def __init__(self):
        self._t0 = 0.0
        self._sent = 0

    def open(self):
        self._t0 = time.monotonic()
        self._sent = 0

    def close(self):
        pass

    def _distance_mm(self, deg):
        """Ray cast from the sensor at (0, 0) in a room spanning x -1.5..2.5, y -1..2.0."""
        t = math.radians(deg)
        dx, dy = math.sin(t), math.cos(t)
        best = math.inf
        for d, lo, hi in ((dx, -1.5, 2.5), (dy, -1.0, 2.0)):
            if d > 1e-9:
                best = min(best, hi / d)
            elif d < -1e-9:
                best = min(best, lo / d)
        px, py, r = -0.6, 1.2, 0.2  # pillar
        b = dx * px + dy * py
        disc = b * b - (px * px + py * py - r * r)
        if disc >= 0 and b - math.sqrt(disc) > 0:
            best = min(best, b - math.sqrt(disc))
        return int(best * 1000)

    def read(self):
        due = int((time.monotonic() - self._t0) * ld06.POINT_RATE / ld06.POINTS_PER_PACKET)
        out = bytearray()
        per = ld06.POINTS_PER_PACKET
        for n in range(self._sent, due):
            start = (n * per * self.STEP_DEG) % 360.0
            readings = [(self._distance_mm(start + i * self.STEP_DEG), 200) for i in range(per)]
            end = start + (per - 1) * self.STEP_DEG
            out += ld06.build_packet(self.SPEED_DPS, start, end, readings, n * 3)
        self._sent = due
        return bytes(out)
