#!/usr/bin/env python3
'''textgrids -- Read and handle Praat’s textgrid files

  © Legisign.org, Tommi Nieminen <software@legisign.org>, 2012-19
  Published under GNU General Public License version 3 or newer.

  2019-07-15  1.3.0   Simplify text-file parsers and get rid of the optional
                      binary= parameter for TextGrid.parse() and
                      TextGrid.read().

'''

import codecs
import io
from collections import OrderedDict, namedtuple
from .transcript import *

# Global constant

version = '1.3.0'

class ParseError(Exception):
    def __str__(self):
        return 'Parse error on line {}'.format(self.args[0])

# Point class
Point = namedtuple('Point', ['text', 'xpos'])

class Interval(object):
    '''Interval is a timeframe xmin..xmax labelled "text".

    xmin, xmax are floats, text a string that is converted into a Transcript
    object.
    '''

    def __init__(self, text=None, xmin=0.0, xmax=0.0):
        self.text = Transcript(text)
        self.xmin = xmin
        self.xmax = xmax
        if self.xmin > self.xmax:
            return ValueError

    def __repr__(self):
        '''Return (semi-)readable representation of self.'''
        return '<Interval text="{}" xmin={} xmax={}>'.format(self.text,
                                                             self.xmin,
                                                             self.xmax)

    def containsvowel(self):
        '''Boolean: Does the label contain a vowel?'''
        global vowels
        return any([vow in self.text for vow in vowels])

    @property
    def dur(self):
        '''Return duration of the Interval.'''
        return self.xmax - self.xmin

    @property
    def mid(self):
        '''Return temporal midpoint for the Interval.'''
        return self.xmin + self.dur / 2

    def startswithvowel(self):
        '''Boolean: does the label start with a vowel?'''
        global vowels
        return any([self.text.startswith(vow) for vow in vowels])

    def timegrid(self, num=3):
        '''Create an even-spaced time grid.

        Takes one optional integer argument "num", the number of timepoints.
        Returns a list of timepoints (floats) where the first element is
        Interval. xmin and the last Interval.xmax.
        '''
        if num <= 1 or num != int(num):
            raise ValueError
        step = self.dur / num
        return [self.xmin + (step * i) for i in range(num + 1)]

class Tier(list):
    '''Tier is a list of either Interval or Point objects.'''

    def __init__(self, data=None, point_tier=False):
        self.is_point_tier = point_tier
        if not data:
            data = []
        super().__init__(data)

    def __add__(self, elem):
        if self.interval_tier and not isinstance(elem, Interval):
            raise TypeError
        elif not isinstance(elem, Point):
            raise TypeError
        super().__add__(elem)

    def concat(self, first=0, last=-1):
        '''Concatenate Intervals Tier[first]...Tier[last].

        first and last follow the usual Python index semantics: starting from
        0, negative number count from the end.

        The method raises an exception if the Tier is a point tier.
        '''
        if not self.interval_tier:
            raise TypeError
        area = self[first:last]
        if area:
            xmin = self[first].xmin
            xmax = self[last].xmax
            text = ''.join([segm.text for segm in area])
            new_segm = Interval(text, xmin, xmax)
            self = self[first:] + new_segm + self[:last]

    def to_csv(self):
        '''Return tier data in CSV-like list, each row a separate string.'''
        if self.is_point_tier:
            return ['"{}";{}'.format(t, xp) for t, xp in self]
        else:
            return ['"{}";{};{}'.format(t, xb, xe) for t, xb, xe in self]

class TextGrid(OrderedDict):
    '''TextGrid is a dict of tier names (keys) and Tiers (values).'''

    def __init__(self, filename=None, binary=False):
        super().__init__({})
        self.filename = filename
        if self.filename:
            self.read(self.filename, binary)

    def __repr__(self):
        '''Return Praat (long) text format representation'''
        buff = ['File type = "ooTextFile"',
                'Object class = "TextGrid"',
                '']
        if self:
            xmin = min([intervals[0].xmin for intervals in self.values()])
            xmax = max([intervals[-1].xmax for intervals in self.values()])
            buff += ['xmin = {}'.format(xmin),
                     'xmax = {}'.format(xmax),
                     'tiers? <exists>',
                     'size = {}'.format(len(self)),
                     'item []:']
            tier_count = 1
            for tier, intervals in self.items():
                buff += ['\titem [{}]:'.format(tier_count),
                        '\t\tclass = "IntervalTier"',
                        '\t\tname = "{}"'.format(tier),
                        '\t\txmin = {}'.format(intervals[0].xmin),
                        '\t\txmax = {}'.format(intervals[-1].xmax),
                        '\t\tintervals: size = {}'.format(len(intervals))]
                for index, interval in enumerate(intervals):
                    buff += ['\t\tintervals [{}]:'.format(index + 1),
                            '\t\t\txmin = {}'.format(interval.xmin),
                            '\t\t\txmax = {}'.format(interval.xmax),
                            '\t\t\ttext = "{}"'.format(interval.text)]
                tier_count += 1
        return '\n'.join([line.replace('\t', '    ') for line in buff])

    def parse(self, data):
        '''Parse textgrid data.

        Obligatory argument "data" is bytes.
        '''
        if not isinstance(data, bytes):
            raise TypeError
        binary = b'ooBinaryFile\x08TextGrid'
        text = ['File type = "ooTextFile"', 'Object class = "TextGrid"', '']
        # Check and then discard binary header
        if data[:len(binary)] == binary:
            buff = io.BytesIO(data[len(binary):])
            self._parse_binary(buff)
        else:
            coding = 'utf-8'
            # Note and then discard BOM
            if data[:2] == b'\xfe\xff':
                coding = 'utf-16-be'
                data = data[2:]
            # Now convert to a text buffer
            buff = [s.strip() for s in data.decode(coding).split('\n')]
            # Check and then discard header
            if buff[:len(text)] != text:
                raise TypeError
            buff = buff[len(text):]
            # If the next line starts with a number, this is a short textgrid
            if buff[0][0] in '-0123456789':
                self._parse_short(buff)
            else:
                self._parse_long(buff)

    def _parse_long(self, data):
        '''Parse LONG textgrid files. Not meant to be used directly.'''
        grok = lambda s: s.split(' = ')[1]
        self.xmin, self.xmax = [float(grok(s)) for s in data[:2]]
        if data[2] != 'tiers? <exists>':
            return
        tiers = int(grok(data[3]))
        p = 6
        for i in range(tiers):
            tier_type, tier_name = [grok(s).strip('"') for s in data[p:p + 2]]
            tier = Tier(point_tier=(tier_type != 'IntervalTier'))
            tier_xmin, tier_xmax = [float(grok(s)) for s in data[p + 2:p + 4]]
            tier_len = int(grok(data[p + 4]))
            p += 6
            for j in range(tier_len):
                if tier.is_point_tier:
                    x1 = float(grok(data[p]))
                    text = Transcript(grok(data[p + 1]).strip('"'))
                    tier.append(Point(text, x1))
                    p += 3
                else:
                    x0, x1 = [float(grok(s)) for s in data[p:p + 2]]
                    text = Transcript(grok(data[p + 2]).strip('"'))
                    tier.append(Interval(text, x0, x1))
                    p += 4
            self[tier_name] = tier

    def _parse_short(self, data):
        '''Parse SHORT textgrid files. Not meant to be used directly.'''
        self.xmin, self.xmax = [float(s) for s in data[:2]]
        if data[2] != '<exists>':
            return
        tiers = int(data[3])
        p = 4
        for i in range(tiers):
            tier_type, tier_name = [s.strip('"') for s in data[p:p + 2]]
            print('{} "{}"'.format(tier_type, tier_name))
            tier = Tier(point_tier=(tier_type == 'PointTier'))
            p += 4
            elems = int(data[p])
            p += 1
            for j in range(elems):
                if is_point_tier:
                    x1, text = data[p:p + 2]
                    x1 = float(x1)
                    text = Transcript(text.strip('"'))
                    tier.append(Point(text, x1))
                    p += 2
                else:
                    x0, x1, text = data[p:p + 3]
                    x0 = float(x0)
                    x1 = float(x1)
                    text = Transcript(text.strip('"'))
                    tier.append(Interval(text, x0, x1))
                    p += 3
            self[tier_name] = tier

    def _parse_binary(self, data):
        '''Parse BINARY textgrid files. Not meant to be used directly.'''
        import struct

        sBool, sByte, sShort, sInt, sDouble = [struct.calcsize(c) for c in '?Bhid']

        self.xmin, self.xmax = struct.unpack('>2d', data.read(2 * sDouble))
        if not struct.unpack('?', data.read(sBool))[0]:
            return

        tiers = struct.unpack('>i', data.read(sInt))[0]
        for i in range(tiers):
            size = struct.unpack('B', data.read(sByte))[0]
            desc = data.read(size)
            if desc == b'PointTier':
                point_tier = True
            elif desc == b'IntervalTier':
                point_tier = False
            else:
                raise ParseError
            tier = Tier(point_tier=point_tier)
            size = struct.unpack('>h', data.read(sShort))[0]
            tier_name = data.read(size).decode()
            # Discard tier xmin, xmax as redundant
            data.read(2 * sDouble)
            elems = struct.unpack('>i', data.read(sInt))[0]
            for j in range(elems):
                if point_tier:
                    xpos = struct.unpack('>d', data.read(sDouble))[0]
                else:
                    xmin, xmax = struct.unpack('>2d', data.read(2 * sDouble))
                size = struct.unpack('>h', data.read(sShort))[0]
                # Apparently size -1 is an index that UTF-16 follows
                if size == -1:
                    size = struct.unpack('>h', data.read(sShort))[0] * 2
                    coding = 'utf-16-be'
                else:
                    coding = 'ascii'
                text = Transcript(data.read(size).decode(coding))
                if point_tier:
                    tier.append(Point(text, xpos))
                else:
                    tier.append(Interval(text, xmin, xmax))
            self[tier_name] = tier

    def read(self, filename):
        '''Read given file as a TextGrid.

        "filename" is the name of the file.
        '''
        self.filename = filename
        with open(self.filename, 'rb') as infile:
            data = infile.read()
        self.parse(data)

    def tier_from_csv(self, tier_name, filename):
        '''Import CSV file to an interval or point tier.

        "tier_name" (string) is the name for the new tier.
        "filename" (string) is the name of the input file.
        '''
        import csv
        tier = None
        with open(filename, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            for line in reader:
                if len(line) == 2:
                    text, xpos = line
                    elem = Point(text, xpos)
                elif len(line) == 3:
                    text, xmin, xmax = line
                    elem = Interval(text, xmin, xmax)
                else:
                    raise ValueError
                if not tier:
                    if isinstance(elem, Point):
                        tier = Tier(point_tier=True)
                    else:
                        tier = Tier()
                # The following raises an exception if the CSV file contains
                # both intervals and points
                tier.append(elem)
        self[tier_name] = tier

    def tier_to_csv(self, tier_name, filename):
        '''Export given tier into a CSV file.

        "tier_name" is the name of the (existing) tier to be exported.
        "filename" is the name of the file.
        '''
        with open(filename, 'w') as csvfile:
            csvfile.write('\n'.join(self[tier_name].csv()))

    def write(self, filename):
        '''Write the text grid into a Praat TextGrid file.

        "filename" is the name of the file.
        '''
        with open(filename, 'w') as f:
            f.write(str(self))

# A simple test if run as script
if __name__ == '__main__':
    import sys
    import os.path

    # Error messages
    E_IOERR = 'I/O error accessing: "{}"'
    E_NOTFOUND = 'File not found: "{}"'
    E_PARSE = 'Parse error: file "{}", line {}'
    E_PERMS = 'No permission to read: "{}"'

    if len(sys.argv) == 1:
        print('Usage: {} FILE...'.format(sys.argv[0]))
        sys.exit(0)

    for arg in sys.argv[1:]:
        try:
            textgrid = TextGrid(arg)
        except FileNotFoundError:
            print(E_NOTFOUND.format(arg), file=sys.stderr)
            continue
        except PermissionError:
            print(E_PERMS.format(arg), file=sys.stderr)
        except IOError:
            print(E_IOERR.format(arg), file=sys.stderr)
            continue
        except ParseError as exc:
            print(E_PARSE.format(arg, exc.args[0]), file=sys.stderr)
            continue
        # Print in long format
        print(textgrid)
