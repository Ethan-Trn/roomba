"""LD06 lidar protocol: bytes in, packets and scans out.

Pure Python. No ROS and no serial port in here, so it can be tested anywhere.

Packet layout (47 bytes, little-endian):
    0      header     0x54
    1      ver_len    0x2C
    2-3    speed      degrees per second
    4-5    start      angle in 0.01 degrees
    6-41   12 points  each: distance (mm, uint16), intensity (uint8)
    42-43  end        angle in 0.01 degrees
    44-45  timestamp  ms
    46     crc8       over bytes 0..45

Angles from the sensor grow clockwise, with 0 at the front of the sensor.
"""
import math
import struct
from dataclasses import dataclass, field

HEADER = 0x54
VER_LEN = 0x2C
PACKET_SIZE = 47
POINTS_PER_PACKET = 12
POINT_RATE = 4500  # points per second at the default 10 Hz spin

RANGE_MIN_M = 0.02
RANGE_MAX_M = 12.0

_FORMAT = '<BBHH' + 'HB' * POINTS_PER_PACKET + 'HHB'
assert struct.calcsize(_FORMAT) == PACKET_SIZE


def _make_crc_table(poly=0x4D):
    """Build the CRC-8 table (MSB first, init 0, no final xor)."""
    table = []
    for byte in range(256):
        crc = byte
        for _ in range(8):
            crc = ((crc << 1) ^ poly) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
        table.append(crc)
    return table


CRC_TABLE = _make_crc_table()


def crc8(data):
    """Return the LD06 CRC-8 of a bytes-like object."""
    crc = 0
    for b in data:
        crc = CRC_TABLE[(crc ^ b) & 0xFF]
    return crc


@dataclass(frozen=True)
class Point:
    """One measurement. angle is degrees clockwise from the front."""

    angle: float
    distance_m: float
    intensity: int


@dataclass(frozen=True)
class Packet:
    """One decoded 47-byte packet."""

    speed_dps: int
    start_angle: float
    end_angle: float
    timestamp_ms: int
    points: tuple


def decode_packet(raw):
    """Decode exactly 47 bytes. Returns None if the packet is not valid."""
    if len(raw) != PACKET_SIZE or raw[0] != HEADER or raw[1] != VER_LEN:
        return None
    if crc8(raw[:-1]) != raw[-1]:
        return None
    f = struct.unpack(_FORMAT, raw)
    speed, start = f[2], f[3]
    pts = f[4:4 + 2 * POINTS_PER_PACKET]
    end, stamp = f[4 + 2 * POINTS_PER_PACKET], f[5 + 2 * POINTS_PER_PACKET]

    span = ((end + 36000 - start) % 36000) / 100.0
    # A packet should cover about speed * 12 / 4500 degrees. Reject wild ones.
    if speed > 0 and span > speed * POINTS_PER_PACKET / POINT_RATE * 1.5:
        return None
    step = span / (POINTS_PER_PACKET - 1)
    points = tuple(
        Point((start / 100.0 + i * step) % 360.0, pts[2 * i] / 1000.0, pts[2 * i + 1])
        for i in range(POINTS_PER_PACKET)
    )
    return Packet(speed, start / 100.0, end / 100.0, stamp, points)


def build_packet(speed_dps, start_deg, end_deg, readings, timestamp_ms=0):
    """Build a valid packet. readings is 12 (distance_mm, intensity) pairs."""
    assert len(readings) == POINTS_PER_PACKET
    values = [HEADER, VER_LEN, speed_dps, round(start_deg * 100) % 36000]
    for dist, inten in readings:
        values += [int(dist), int(inten)]
    values += [round(end_deg * 100) % 36000, timestamp_ms & 0xFFFF]
    body = struct.pack(_FORMAT[:-1], *values)
    return body + bytes([crc8(body)])


class PacketParser:
    """Turns a raw byte stream into packets, resyncing after garbage."""

    def __init__(self):
        self._buf = bytearray()
        self.good = 0
        self.bad = 0

    def feed(self, data):
        """Add bytes. Returns a list of the packets completed by them."""
        buf = self._buf
        buf += data
        out = []
        while True:
            i = buf.find(HEADER)
            if i < 0:
                buf.clear()
                break
            if i > 0:
                del buf[:i]
            if len(buf) < 2:
                break
            if buf[1] != VER_LEN:
                del buf[0]
                continue
            if len(buf) < PACKET_SIZE:
                break
            pkt = decode_packet(bytes(buf[:PACKET_SIZE]))
            if pkt is None:
                self.bad += 1
                del buf[0]
                continue
            del buf[:PACKET_SIZE]
            self.good += 1
            out.append(pkt)
        return out


@dataclass
class Scan:
    """One full turn, in ROS convention (counter-clockwise, 0 at the front).

    Every point of the turn is kept, sorted by angle. Points with no valid
    reading are inf so the spacing stays even.
    """

    ranges: list
    intensities: list
    angle_min: float  # radians
    angle_max: float
    angle_increment: float
    range_min: float = RANGE_MIN_M
    range_max: float = RANGE_MAX_M
    count: int = 0  # points with a valid reading


class ScanAssembler:
    """Collects the points of one turn and hands them over when the turn ends."""

    def __init__(self):
        self._last_angle = None
        self._first_turn = True
        self._points = []

    def _finish(self):
        # sensor angles grow clockwise, ROS wants counter-clockwise
        pts = sorted((((360.0 - p.angle) % 360.0, p) for p in self._points),
                     key=lambda t: t[0])
        if len(pts) < 2:
            return None
        ranges, inten, valid = [], [], 0
        for _, p in pts:
            if RANGE_MIN_M <= p.distance_m <= RANGE_MAX_M:
                ranges.append(p.distance_m)
                valid += 1
            else:
                ranges.append(math.inf)
            inten.append(float(p.intensity))
        lo, hi = math.radians(pts[0][0]), math.radians(pts[-1][0])
        return Scan(ranges, inten, lo, hi, (hi - lo) / (len(pts) - 1), count=valid)

    def add(self, pkt):
        """Add a packet. Returns a finished Scan when a turn completes.

        The turn is cut at the exact point where the angle wraps past 360,
        even if that happens in the middle of a packet.
        """
        done = None
        for p in pkt.points:
            if self._last_angle is not None and p.angle < self._last_angle - 180.0:
                if not self._first_turn:  # the first turn is partial, drop it
                    done = self._finish()
                self._first_turn = False
                self._points = []
            self._last_angle = p.angle
            self._points.append(p)
        return done
