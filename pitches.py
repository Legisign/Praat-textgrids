#!/usr/bin/env python3
'''

  pitches.py -- an extremely simple Praat Pitch object parser.

  2019-01-07    Started. (TN)

'''

from collections import namedtuple

Measurement = namedtuple('Measurement', ['t', 'f0'])

class Pitch(list):
    def __init__(self, filename=None):
        self.filename = filename
        if self.filename:
            self.read(filename)

    def __str__(self):
        return '\n'.join(['{:.3f};{:.2f}'.format(t, f0) for t, f0 in self])

    def read(self, filename):
        def getval(s):
            return float(s.split(' = ')[1])

        self.filename = filename
        with open(filename, 'r') as infile:
            i = 0
            skip = True
            for line in infile:
                if line.startswith('xmin ='):
                    xmin = getval(line)
                elif line.startswith('xmax ='):
                    xmax = getval(line)
                elif line.startswith('dx = '):
                    dx = getval(line)
                elif 'candidate [1]' in line:
                    skip = False
                elif not skip and 'frequency =' in line:
                    freq = getval(line)
                    skip = True
                    self.append(Measurement(xmin + i * dx, freq))
                    i += 1

if __name__ == '__main__':
    import sys

    for arg in sys.argv[1:]:
        pitch = Pitch(arg)
        print(pitch)
