from roomba.oi.roomba import Roomba, STRAIGHT, TURN_CW


class Fake:
    def __init__(self, reply=b''):
        self.sent, self.reply = b'', reply

    def write(self, b):
        self.sent += b

    def read(self, n):
        out, self.reply = self.reply[:n], self.reply[n:]
        return out

    def reset_input_buffer(self):
        pass


def make(reply=b''):
    f = Fake(reply)
    return Roomba(serial_port=f), f


def test_drive_direct_right_first():
    r, f = make()
    r.drive_direct(100, -200)
    assert f.sent == bytes([145, 0xFF, 0x38, 0x00, 0x64])


def test_drive_straight_and_spin():
    r, f = make()
    r.drive(300, STRAIGHT)
    r.drive(100, TURN_CW)
    assert f.sent == bytes([137, 1, 44, 0x80, 0, 137, 0, 100, 0xFF, 0xFF])


def test_sensor():
    r, f = make(bytes([0x3E, 0x80]))
    assert r.sensor('voltage') == 16000
    assert f.sent == bytes([142, 22])


def test_wait_for_roomba():
    r, f = make(b'\x00')
    r.wait_for_roomba()
    assert f.sent == bytes([128, 142, 7])
