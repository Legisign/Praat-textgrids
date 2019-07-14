#!/usr/bin/env python3
'''textgrids -- Read and handle Praat’s textgrid files

  © Legisign.org, Tommi Nieminen <software@legisign.org>, 2012-19
  Published under GNU General Public License version 3 or newer.

  2019-07-11  1.2.0   Read binary textgrids.

'''

import codecs
import re
import struct
from collections import OrderedDict, namedtuple
from .transcript import *

# Global constant

version = '1.2.0'

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

    def parse(self, data, binary=False):
        '''Parse textgrid data.

        Obligatory argument "data" is either str or bytes. Optional argument
        "binary" is required when parsing binary data.
        '''
        if binary:
            self._parse_binary(data)
        else:
            filetype, objclass, separ = data[:3]
            if filetype != 'File type = "ooTextFile"' or \
               objclass != 'Object class = "TextGrid"' or \
               separ != '':
               raise ParseError
            if re.match('^-?\d+.?\d*$', data[3]):
                self._parse_short(data[3:])
            else:
                self._parse_long(data[3:])

    def _parse_long(self, data):
        '''Parse LONG textgrid files. Not meant to be used directly.'''

        def keyval(s):
            '''Handy key–value type conversions.'''
            kv = re.compile('^\s*(.+)\s+=\s+(.+)$')
            k, v = kv.match(s).groups()
            if v.startswith('"'):
                v = v.strip('"')
            else:
                v = float(v)
            return k, v

        self.xmin, self.xmax = [float(line.split()[-1]) for line in data[:2]]
        if '<exists>' not in data[2]:
            return
        new_tier = re.compile(r'^item \[\d+\]:$')
        new_interval = re.compile(r'^intervals \[\d+\]:$')
        new_point = re.compile(r'^points \[\d+\]:$')
        new_value = re.compile(r'(name|xmin|xmax|xpos|text) = "?.*"?$')
        tier = []
        for lineno, line in enumerate(data[5:], 9):
            if new_tier.match(line):
                if tier:
                    self[name] = tier
                    name = None
                    tier = None
            elif new_interval.match(line) and not tier:
                tier = Tier()
            elif new_point.match(line) and not tier:
                tier = Tier(point_tier=True)
            elif new_value.match(line):
                try:
                    key, val = keyval(line)
                except ValueError:
                    raise ParseError(lineno)
                if key == 'name':
                    name = val
                elif key == 'xmin':
                    if not isinstance(val, float):
                        raise ParseError(lineno)
                    x0 = val
                elif key in ('xmax', 'xpos'):
                    if not isinstance(val, float):
                        raise ParseError(lineno)
                    x1 = val
                elif key == 'text':
                    if tier.is_point_tier:
                        elem = Point(val, x1)
                    else:
                        elem = Interval(Transcript(val), x0, x1)
                    tier.append(elem)
        if tier:
            self[name] = tier

    def _parse_short(self, data):
        '''Parse SHORT textgrid files. Not meant to be used directly.'''
        self.xmin, self.xmax = [float(num) for num in data[:2]]
        if data[2] != '<exists>':
            return
        # tier = []
        mode = 'type'
        for lineno, line in enumerate(data[4:], 8):
            if mode == 'type':
                tier = Tier(point_tier=(line != '"IntervalTier"'))
                mode = 'name'
            elif mode == 'name':
                name = line.strip('"')
                mode = 'tmin'
            elif mode == 'tmin':
                tmin = float(line)
                mode = 'tmax'
            elif mode == 'tmax':
                tmax = float(line)
                mode = 'tlen'
            elif mode == 'tlen':
                tlen = int(line)
                mode = 'xmop' if tier.is_point_tier else 'xmin'
            elif mode == 'xmin':
                try:
                    x0 = float(line)
                except ValueError:
                    raise ParseError(lineno)
                mode = 'xmop'
            elif mode == 'xmop':
                try:
                    x1 = float(line)
                except ValueError:
                    raise ParseError(lineno)
                mode = 'text'
            elif mode == 'text':
                if tier.is_point_tier:
                    tier.append(Point(line.strip('"'), x1))
                else:
                    tier.append(Interval(line.strip('"') , x0, x1))
                if len(tier) == tlen:
                    self[name] = tier
                    name = None
                    tier = None
                    mode = 'type'
                else:
                    mode = 'xmin'

    def _parse_binary(self, infile):
        '''Parse BINARY textgrid files. Not meant to be used directly.'''
        signature = b'ooBinaryFile\x08TextGrid'
        sBool, sByte, sShort, sInt, sDouble = [struct.calcsize(c) for c in '?Bhid']

        if infile.read(len(signature)) != signature:
            raise ParseError

        self.xmin, self.xmax = struct.unpack('>2d', infile.read(2 * sDouble))
        if not struct.unpack('?', infile.read(sBool))[0]:
            return

        tiers = struct.unpack('>i', infile.read(sInt))[0]
        for i in range(tiers):
            size = struct.unpack('B', infile.read(sByte))[0]
            desc = infile.read(size)
            if desc == b'PointTier':
                point_tier = True
            elif desc == b'IntervalTier':
                point_tier = False
            else:
                raise ParseError
            tier = Tier(point_tier=point_tier)
            size = struct.unpack('>h', infile.read(sShort))[0]
            tier_name = infile.read(size).decode()
            # Discard tier xmin, xmax as redundant
            infile.read(2 * sDouble)
            elems = struct.unpack('>i', infile.read(sInt))[0]
            for j in range(elems):
                if point_tier:
                    xpos = struct.unpack('>d', infile.read(sDouble))[0]
                else:
                    xmin, xmax = struct.unpack('>2d', infile.read(2 * sDouble))
                size = struct.unpack('>h', infile.read(sShort))[0]
                # Apparently size -1 is an index that UTF-16 follows
                if size == -1:
                    size = struct.unpack('>h', infile.read(sShort))[0] * 2
                    coding = 'utf-16-be'
                else:
                    coding = 'ascii'
                text = Transcript(infile.read(size).decode(coding))
                if point_tier:
                    tier.append(Point(text, xpos))
                else:
                    tier.append(Interval(text, xmin, xmax))
            self[tier_name] = tier

    def read(self, filename, binary=False):
        '''Read given file as a TextGrid.

        "filename" is the name of the file.
        '''
        self.filename = filename
        if binary:
            with open(self.filename, 'rb') as infile:
                self.parse(infile, binary=True)
        else:
            # Praat uses UTF-16 or UTF-8 with no apparent pattern
            try:
                with codecs.open(self.filename, 'r', 'UTF-16') as infile:
                    buff = [line.strip() for line in infile]
            except UnicodeError:
                with open(self.filename, 'r') as infile:
                    buff = [line.strip() for line in infile]
            self.parse(buff)

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
