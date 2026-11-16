"""Roomba 600 Open Interface. Call a method; the serial bytes are handled here."""
import struct
import time
import serial

STRAIGHT = 32768   # drive() radius: straight
TURN_CW = -1       # drive() radius: spin clockwise
TURN_CCW = 1       # drive() radius: spin counter-clockwise

# name -> (packet id, bytes, signed)
SENSORS = {
    'bumps_wheeldrops': (7, 1, False), 'wall': (8, 1, False),
    'cliff_left': (9, 1, False), 'cliff_front_left': (10, 1, False),
    'cliff_front_right': (11, 1, False), 'cliff_right': (12, 1, False),
    'virtual_wall': (13, 1, False), 'dirt_detect': (15, 1, False),
    'buttons': (18, 1, False), 'distance': (19, 2, True),
    'angle': (20, 2, True), 'charging_state': (21, 1, False),
    'voltage': (22, 2, False), 'current': (23, 2, True),
    'temperature': (24, 1, True), 'battery_charge': (25, 2, False),
    'battery_capacity': (26, 2, False), 'oi_mode': (35, 1, False),
    'right_encoder': (43, 2, False), 'left_encoder': (44, 2, False),
    'light_bumper': (45, 1, False),
}


def _clamp(x, lo, hi):
    return max(lo, min(hi, int(x)))


class Roomba:
    def __init__(self, port='/dev/ttyUSB0', baud=115200, serial_port=None):
        self.port, self.baud = port, baud
        self.s = serial_port   # pass a fake in tests

    #connection
    def open(self, wait=True):
        if self.s is None:
            
            self.s = serial.Serial(self.port, self.baud, timeout=0.2)
        if wait:
            self.wait_for_roomba()
        else:
            self.start()

    def close(self):
        if self.s is not None:
            self.s.close()
            self.s = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()

    def _send(self, *data):
        buf = bytearray()
        for d in data:
            buf += d if isinstance(d, (bytes, bytearray)) else bytes([d & 0xFF])
        self.s.write(bytes(buf))

    def wait_for_roomba(self):
        print("Waiting for Roomba... press Clean")
        while True:
            self.s.write(bytes([128]))        # START
            time.sleep(0.1)
            self.s.reset_input_buffer()
            self.s.write(bytes([142, 7]))     # ask for sensor packet 7
            if self.s.read(1):                # any reply = it's awake and listening
                print("Roomba is awake")
                return
            time.sleep(0.2)

    #modes
    def start(self):
        self._send(128)

    def safe(self):
        self._send(131)
        time.sleep(0.1)

    def full(self):
        self._send(132)
        time.sleep(0.1)

    def power(self):
        self._send(133)

    def reset(self):
        self._send(7)

    def stop(self):
        self._send(173)

    #cleaning
    def clean(self):
        self._send(135)

    def spot(self):
        self._send(134)

    def dock(self):
        self._send(143)

    #driving
    def drive(self, velocity, radius=STRAIGHT, duration=0):
        """velocity mm/s (-500..500); radius mm (-2000..2000), STRAIGHT,
        TURN_CW or TURN_CCW. duration s: 0 = keep driving, otherwise drive
        for that long then stop."""
        v = _clamp(velocity, -500, 500)
        if radius not in (STRAIGHT, TURN_CW, TURN_CCW):
            radius = _clamp(radius, -2000, 2000)
        self._send(137, struct.pack('>HH', v & 0xFFFF, radius & 0xFFFF))
        if duration:
            time.sleep(duration)
            self.stop_moving()

    def drive_direct(self, left, right, duration=0):
        """Wheel speeds in mm/s (-500..500). duration s: 0 = keep driving,
        otherwise drive for that long then stop."""
        lf, rt = _clamp(left, -500, 500), _clamp(right, -500, 500)
        self._send(145, struct.pack('>hh', rt, lf))   # OI wants right first
        if duration:
            time.sleep(duration)
            self.stop_moving()

    def stop_moving(self):
        self.drive_direct(0, 0)

    #motors / lights / sound
    def motors(self, main_brush=False, vacuum=False, side_brush=False):
        self._send(138, side_brush << 0 | vacuum << 1 | main_brush << 2)

    def leds(self, debris=False, spot=False, dock=False, check_robot=False,
             color=0, intensity=0):
        """Power LED: color 0 green .. 255 red, intensity 0..255."""
        self._send(139, debris | spot << 1 | dock << 2 | check_robot << 3,
                   _clamp(color, 0, 255), _clamp(intensity, 0, 255))

    def digits(self, text):
        """Show up to 4 ASCII characters on the display."""
        self._send(164, text.ljust(4)[:4].encode('ascii'))

    def song(self, number, notes):
        """number 0..3, notes = [(midi_note, duration_in_64ths), ...] max 16."""
        self._send(140, number, len(notes),
                   b''.join(bytes([n, d]) for n, d in notes))

    def play(self, number):
        self._send(141, number)

    def beep(self):
        self.song(3, [(72, 16)])
        self.play(3)

    #sensors
    def sensor(self, name):
        """e.g. r.sensor('voltage') -> int. See SENSORS for names."""
        pid, size, signed = SENSORS[name]
        self.s.reset_input_buffer()
        self._send(142, pid)
        data = self.s.read(size)
        if len(data) != size:
            raise TimeoutError(f'no reply for {name}')
        return int.from_bytes(data, 'big', signed=signed)

    def bumpers(self):
        b = self.sensor('bumps_wheeldrops')
        return {'bump_right': bool(b & 1), 'bump_left': bool(b & 2),
                'wheeldrop_right': bool(b & 4), 'wheeldrop_left': bool(b & 8)}
