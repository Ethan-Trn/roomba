import math

from roomba.lidar import ld06
from roomba.lidar.sources import SimulatedSource


def _packet(start=10.0, dist=1000):
    end = start + 11 * 0.8
    return ld06.build_packet(3600, start, end, [(dist, 100)] * 12, 5)


def test_crc_table_matches_vendor():
    t = ld06.CRC_TABLE
    assert t[:8] == [0x00, 0x4D, 0x9A, 0xD7, 0x79, 0x34, 0xE3, 0xAE]
    assert t[0x80] == 0x7C


def test_decode_round_trip():
    pkt = ld06.decode_packet(_packet(10.0, 1500))
    assert pkt.speed_dps == 3600
    assert pkt.start_angle == 10.0
    assert math.isclose(pkt.points[11].angle, 18.8, abs_tol=0.02)
    assert pkt.points[0].distance_m == 1.5


def test_bad_crc_rejected():
    raw = bytearray(_packet())
    raw[10] ^= 0xFF
    assert ld06.decode_packet(bytes(raw)) is None


def test_angle_wraps_past_360():
    pkt = ld06.decode_packet(ld06.build_packet(3600, 355.0, 3.8, [(1000, 1)] * 12))
    angles = [p.angle for p in pkt.points]
    assert all(0 <= a < 360 for a in angles)
    assert angles[0] == 355.0 and math.isclose(angles[-1], 3.8, abs_tol=0.02)


def test_parser_resyncs_after_garbage_and_split_reads():
    parser = ld06.PacketParser()
    stream = b'\x00\x54\x99\x54' + _packet(0.0) + b'\x54\x2c' + _packet(9.6)
    got = []
    for i in range(0, len(stream), 7):  # arrives in awkward chunks
        got += parser.feed(stream[i:i + 7])
    assert len(got) == 2
    assert got[1].start_angle == 9.6


def test_assembler_keeps_every_point_of_a_turn():
    sim = SimulatedSource()
    parser, asm = ld06.PacketParser(), ld06.ScanAssembler()
    scans = []
    for n in range(3 * 38):  # about three turns of packets
        start = (n * 9.6) % 360
        raw = ld06.build_packet(3600, start, start + 8.8,
                                [(sim._distance_mm(start + i * 0.8), 200) for i in range(12)])
        for pkt in parser.feed(raw):
            s = asm.add(pkt)
            if s:
                scans.append(s)
    assert scans
    scan = scans[-1]
    assert 445 <= len(scan.ranges) <= 452  # about 450, no overlap past 360
    assert scan.count == len(scan.ranges)
    degrees = [math.degrees(scan.angle_min + i * scan.angle_increment) for i in range(len(scan.ranges))]
    assert max(degrees) <= 360 and min(degrees) >= 0
    assert math.isclose(scan.angle_increment, math.radians(0.8), rel_tol=0.1)
    # Angles are sorted counter-clockwise. Straight ahead is 2.0 m in the sim.
    near_front = [r for i, r in enumerate(scan.ranges)
                  if abs(scan.angle_min + i * scan.angle_increment) < math.radians(2)]
    assert near_front and all(1.9 < r < 2.1 for r in near_front)
