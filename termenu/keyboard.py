from __future__ import with_statement
from __future__ import print_function

import os
import sys
import fcntl
import termios
import select
import errno
from . import ansi

STDIN = sys.stdin.fileno()

ANSI_SEQUENCES = dict(
    up = '\x1b[A',
    down = '\x1b[B',
    right = '\x1b[C',
    left = '\x1b[D',
    home = '\x1bOH',
    end = '\x1bOF',
    insert = '\x1b[2~',
    pageUp = '\x1b[5~',
    pageDown = '\x1b[6~',
    backspace = '\x7f',
    ctrl_B = '\x02',
    ctrl_E = '\x05',
    ctrl_F = '\x06',
    ctrl_R = '\x12',
    ctrl_W = '\x17',
    F1 = '\x1bOP',
    F2 = '\x1bOQ',
    F3 = '\x1bOR',
    F4 = '\x1bOS',
    F5 = '\x1b[15~',
    F6 = '\x1b[17~',
    F7 = '\x1b[18~',
    F8 = '\x1b[19~',
    F9 = '\x1b[20~',
    F10 = '\x1b[21~',
    F11 = '\x1b[23~',
    F12 = '\x1b[24~',
    ctrl_F1 = '\x1b[1;5P',
    ctrl_F2 = '\x1b[1;5Q',
    ctrl_F3 = '\x1b[1;5R',
    ctrl_F4 = '\x1b[1;5S',
    ctrl_F5 = '\x1b[15;5~',
    ctrl_F6 = '\x1b[17;5~',
    ctrl_F7 = '\x1b[18;5~',
    ctrl_F8 = '\x1b[19;5~',
    ctrl_F9 = '\x1b[20;5~',
    ctrl_F10 = '\x1b[21;5',
    ctrl_F11 = '\x1b[23;5~',
    ctrl_F12 = '\x1b[24;5~',
    shift_F1 = '\x1b[1;2P',
    shift_F2 = '\x1b[1;2Q',
    shift_F3 = '\x1b[1;2R',
    shift_F4 = '\x1b[1;2S',
    shift_F5 = '\x1b[15;2~',
    shift_F6 = '\x1b[17;2~',
    shift_F7 = '\x1b[18;2~',
    shift_F8 = '\x1b[19;2~',
    shift_F9 = '\x1b[20;2~',
    shift_F10 = '\x1b[21;2~',
    shift_F11 = '\x1b[23;2~',
    shift_F12 = '\x1b[24;2~',
    ctrl_shift_F1 = '\x1b[1;6P',
    ctrl_shift_F2 = '\x1b[1;6Q',
    ctrl_shift_F3 = '\x1b[1;6R',
    ctrl_shift_F4 = '\x1b[1;6S',
    ctrl_shift_F5 = '\x1b[15;6~',
    ctrl_shift_F6 = '\x1b[17;6~',
    ctrl_shift_F7 = '\x1b[18;6~',
    ctrl_shift_F8 = '\x1b[19;6~',
    ctrl_shift_F9 = '\x1b[20;6~',
    ctrl_shift_F10 = '\x1b[21;6~',
    ctrl_shift_F11 = '\x1b[23;6~',
    ctrl_shift_F12 = '\x1b[24;6~',
    alt_shift_F1 = '\x1b[1;4P',
    alt_shift_F2 = '\x1b[1;4Q',
    alt_shift_F3 = '\x1b[1;4R',
    alt_shift_F4 = '\x1b[1;4S',
    alt_shift_F5 = '\x1b[15;4~',
    alt_shift_F6 = '\x1b[17;4~',
    alt_shift_F7 = '\x1b[18;4~',
    alt_shift_F8 = '\x1b[19;4~',
    alt_shift_F9 = '\x1b[20;4~',
    alt_shift_F10 = '\x1b[21;4~',
    alt_shift_F11 = '\x1b[23;4~',
    alt_shift_F12 = '\x1b[24;4~',
    ctrl_alt_shift_F1 = '\x1b[1;8P',
    ctrl_alt_shift_F2 = '\x1b[1;8Q',
    ctrl_alt_shift_F3 = '\x1b[1;8R',
    ctrl_alt_shift_F4 = '\x1b[1;8S',
    ctrl_alt_shift_F5 = '\x1b[15;8~',
    ctrl_alt_shift_F6 = '\x1b[17;8~',
    ctrl_alt_shift_F7 = '\x1b[18;8~',
    ctrl_alt_shift_F8 = '\x1b[19;8~',
    ctrl_alt_shift_F9 = '\x1b[20;8~',
    ctrl_alt_shift_F10 = '\x1b[21;8~',
    ctrl_alt_shift_F11 = '\x1b[23;8~',
    ctrl_alt_shift_F12 = '\x1b[24;8~'
)

KEY_NAMES = dict((v,k) for k,v in ANSI_SEQUENCES.items())
KEY_NAMES.update({
    '\x1b' : 'esc',
    '\n' : 'enter',
    '\x7f' : 'delete',
    ' ': 'space',
    '\x7f' : 'backspace',
})#^[[3~

class RawTerminal(object):
    def __init__(self, blocking=True):
        self._blocking = blocking

    def open(self):
        # Set raw mode
        self._oldterm = termios.tcgetattr(STDIN)
        newattr = termios.tcgetattr(STDIN)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(STDIN, termios.TCSANOW, newattr)

        # Set non-blocking IO on stdin
        self._old = fcntl.fcntl(STDIN, fcntl.F_GETFL)
        if not self._blocking:
            fcntl.fcntl(STDIN, fcntl.F_SETFL, self._old | os.O_NONBLOCK)

    def close(self):
        # Restore previous terminal mode
        termios.tcsetattr(STDIN, termios.TCSAFLUSH, self._oldterm)
        fcntl.fcntl(STDIN, fcntl.F_SETFL, self._old)

    def get(self):
        return os.read(sys.stdin.fileno(), 1).decode('ascii')

    def wait(self):
        select.select([STDIN], [], [])

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

def keyboard_listener(heartbeat=None):
    with RawTerminal(blocking=False) as terminal:
        # return keys
        sequence = ""
        while True:
            yielded = False
            # wait for keys to become available
            select.select([STDIN], [], [], heartbeat)
            # read all available keys
            while True:
                try:
                    sequence = sequence + terminal.get()
                except OSError as e:
                    if e.errno == errno.EAGAIN:
                        break
            # handle ANSI key sequences
            while sequence:
                for seq in ANSI_SEQUENCES.values():
                    if sequence[:len(seq)] == seq:
                        yield KEY_NAMES[seq]
                        yielded = True
                        sequence = sequence[len(seq):]
                        break
                # handle normal keys
                else:
                    for key in sequence:
                        yield KEY_NAMES.get(key, key)
                        yielded = True
                    sequence = ""
            if not yielded:
                yield "heartbeat"
    
if __name__ == "__main__":
    for key in keyboard_listener(0.5):
        print(key)

