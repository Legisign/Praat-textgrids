#!/usr/bin/env python3
'''textgrids -- Read and handle Praat’s textgrid files

  © Legisign.org, Tommi Nieminen <software@legisign.org>, 2012-20
  Published under GNU General Public License version 3 or newer.

  2020-03-27  1.4.0.dev1    New ideas from Maxine Fily: tier + tier should
                            work as expected, concatenating tiers.
  2020-03-29  1.4.0.dev2    Fixed Tier.to_csv() bug, but the changes in dev1
                            still need testing.
  2020-03-29  1.4.0.dev3    For tier + tier to work, tier.xmin and tier.xmax
                            should be read after all. Parser changes as well
                            as fixes for Tier.__add__().
  2020-04-05  1.4.0.dev4    Two fixes: Interval.__init__() should RAISE an
                            exception, not return one if xmin > xmax. Also,
                            TextGrid.tier_from_csv() should convert the xpos,
                            xmin, and xmax values read from the CSV to floats.
  2020-04-06  1.4.0.dev5    Trying to set Tier.xmin and Tier.xmax correctly.
  2020-04-06  1.4.0.dev6    Forced conversion of xmin, xmax to floats in
                            Interval.__init__() too. (No doubt the proper way
                            would be to define getter and setter methods but
                            that seems like an overkill.)

'''

import codecs
import io
import struct
from collections import OrderedDict, namedtuple
from .transcript import *
from .templates import *

# Global constant

version = '1.4.0.dev6'

class BinaryError(Exception):
    '''Read error for binary files.'''
    pass

class ParseError(Exception):
    '''Read error for text files.'''
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
        self.xmin = float(xmin)
        self.xmax = float(xmax)
        if self.xmin > self.xmax:
            raise ValueError('xmin > xmax')

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

    def endswithvowel(self):
        '''Boolean: does the label end with a vowel?

        Discards diacritics before testing.'''
        global vowels
        text = self.text.transcode(retain_diacritics=False)
        return any([text.endswith(vow) for vow in vowels])

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
            raise ValueError('value not integer or is <= 1')
        step = self.dur / num
        return [self.xmin + (step * i) for i in range(num + 1)]

class Tier(list):
    '''Tier is a list of either Interval or Point objects.'''

    def __init__(self, data=None, xmin=0.0, xmax=0.0, point_tier=False):
        if not data:
            data = []
        # Use data for xmin and xmax unless they are explicitly given
        if data and xmin == 0.0 and xmax == 0.0:
            xmin = data[0].xmin
            xmax = data[-1].xmax
        self.xmin = float(xmin)
        self.xmax = float(xmax)
        if self.xmin < 0 or self.xmax < 0:
            raise ValueError('value not float or is < 0.0')
        self.is_point_tier = point_tier
        super().__init__(data)

    def __add__(self, tier):
        '''Concatenate tiers.'''
        # Only a tier or the empty list can be concatenated with a tier
        if tier and not isinstance(tier, Tier):
            raise TypeError('incompatible types')
        # Concatenate only tiers of the same type
        if self.is_point_tier != tier.is_point_tier:
            raise TypeError('tier types differ')
        # Sanity check
        if self.xmax > tier.xmin:
            raise ValueError('time values do not match')
        return Tier(super().__add__(tier))

    def merge(self, first=0, last=-1):
        '''Merge intervals Tier[first]...Tier[last].

        Parameters follow the usual Python index semantics: starting from 0,
        negative number count from the end. Note that the tier is not changed
        in place, you have to assign it to a variable.

        The method raises a TypeError if the Tier is a point tier,
        and ValueError if Tier[first:last] is not a slice.
        '''
        if self.is_point_tier:
            raise TypeError
        area = self[first:last + 1]
        if not area:
            raise ValueError
        xmin = self[first].xmin
        xmax = self[last].xmax
        text = ''.join([segm.text for segm in area])
        new = Interval(text, xmin, xmax)
        self = self[:first] + [new] + self[last + 1:]
        return self

    def to_csv(self):
        '''Format tier data as CSV, each row a separate string.'''
        if self.is_point_tier:
            return ['"{}";{}'.format(p.text, p.xpos) for p in self]
        else:
            return ['"{}";{};{}'.format(i.text.transcode(),
                                        i.xmin,
                                        i.xmax) for i in self]

    @property
    def tier_type(self):
        '''Return tier type as string (for convenience).'''
        return 'PointTier' if self.is_point_tier else 'IntervalTier'

class TextGrid(OrderedDict):
    '''TextGrid is a dict of tier names (keys) and Tiers (values).'''

    def __init__(self, filename=None):
        self.xmin = self.xmax = 0.0
        self.filename = filename
        if self.filename:
            self.read(self.filename)

    def __repr__(self):
        '''Return Praat (long) text format representation'''
        return self.format()

    def format(self, fmt=TEXT_LONG):
        '''Format data as long text, short text, or binary.

        The optional argument can be TEXT_LONG (or 0) for long text,
        TEXT_SHORT (or 1) for short text, or BINARY (or 2) for binary.
        '''
        global BINARY, TEXT_LONG, TEXT_SHORT
        if fmt == TEXT_LONG:
            return(self._format_long())
        elif fmt == TEXT_SHORT:
            return(self._format_short())
        elif fmt == BINARY:
            return(self._format_binary())
        else:
            raise ValueError

    def _format_binary(self):
        '''Format self as binary. Not intended to be used directly.'''
        out = b'ooBinaryFile\x08TextGrid'
        out += struct.pack('>2d?i', self.xmin, self.xmax, True, len(self))
        for name, tier in self.items():
            typ = b'PointTier' if tier.is_point_tier else b'IntervalTier'
            out += struct.pack('B', len(typ))
            out += typ
            try:
                encoded_name = bytes(name, encoding='ascii')
                out += struct.pack('>h', len(encoded_name))
            except UnicodeEncodeError:
                encoded_name = bytes(name, encoding='utf-16-be')
                out += struct.pack('>2h', -1, len(encoded_name))
            out += encoded_name
            out += struct.pack('>2di', self.xmin, self.xmax, len(tier))
            for elem in tier:
                if tier.is_point_tier:
                    out += struct.pack('>d', elem.xpos)
                else:
                    out += struct.pack('>2d', elem.xmin, elem.xmax)
                try:
                    encoded_text = bytes(elem.text, encoding='ascii')
                    out += struct.pack('>h', len(encoded_text))
                except UnicodeEncodeError:
                    encoded_text = bytes(elem.text, encoding='utf-16-be')
                    out += struct.pack('>2h', -1, len(encoded_text))
                out += encoded_text
        return out

    def _format_long(self):
        '''Format self as long text. Not intended to be used directly.'''
        global long_header, long_tier, long_point, long_interval
        out = long_header.format(self.xmin, self.xmax, len(self))
        tier_count = 1
        for name, tier in self.items():
            if tier.is_point_tier:
                tier_type = 'PointTier'
                elem_type = 'points'
            else:
                tier_type = 'IntervalTier'
                elem_type = 'intervals'
            out += long_tier.format(tier_count,
                                    tier_type,
                                    name,
                                    self.xmin,
                                    self.xmax,
                                    elem_type,
                                    len(tier))
            for elem_count, elem in enumerate(tier, 1):
                if tier.is_point_tier:
                    out += long_point.format(elem_count,
                                             elem.xpos,
                                             elem.text)
                else:
                    out += long_interval.format(elem_count,
                                                elem.xmin,
                                                elem.xmax,
                                                elem.text)
        return out

    def _format_short(self):
        '''Format self as short text. Not intended to be used directly.'''
        global short_header, short_tier, short_point, short_interval
        out = short_header.format(xmin=self.xmin,
                                  xmax=self.xmax,
                                  length=len(self))
        for name, tier in self.items():
            out += short_tier.format(tier_type=tier.tier_type,
                                     name=name,
                                     xmin=self.xmin,
                                     xmax=self.xmax,
                                     length=len(tier))
            for elem in tier:
                if tier.is_point_tier:
                    out += short_point.format(xpos=elem.xpos,
                                              text=elem.text)
                else:
                    out += short_interval.format(xmin=elem.xmin,
                                                 xmax=elem.xmax,
                                                 text=elem.text)
        return out

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
            try:
                self._parse_binary(buff)
            except (IndexError, ValueError):
                raise BinaryError
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

    def _parse_binary(self, data):
        '''Parse BINARY textgrid files. Not intended to be used directly.'''
        sBool, sByte, sShort, sInt, sDouble = [struct.calcsize(c) for c in '?Bhid']

        self.xmin, self.xmax = struct.unpack('>2d', data.read(2 * sDouble))
        if not struct.unpack('?', data.read(sBool))[0]:
            return

        tiers = struct.unpack('>i', data.read(sInt))[0]
        for i in range(tiers):
            size = struct.unpack('B', data.read(sByte))[0]
            desc = data.read(size)
            # TextTiers don’t appear anywhere in Praat’s UI as far as
            # I can see but they are mentioned in Praat’s online docs.
            # TextTier is just a PointTier with a different name
            # so let’s treat it as one.
            if desc in (b'PointTier', b'TextTier'):
                point_tier = True
            elif desc == b'IntervalTier':
                point_tier = False
            else:
                raise BinaryError
            tier = Tier(point_tier=point_tier)
            size = struct.unpack('>h', data.read(sShort))[0]
            tier_name = data.read(size).decode()
            xmin = data.read(sDouble)
            xmax = data.read(sDouble)
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
            self.xmin = xmin
            self.xmax = xmax

    def _parse_long(self, data):
        '''Parse LONG textgrid files. Not intended to be used directly.'''
        grab = lambda s: s.split(' = ')[1]
        self.xmin, self.xmax = [float(grab(s)) for s in data[:2]]
        if data[2] != 'tiers? <exists>':
            return
        tiers = int(grab(data[3]))
        p = 6
        for i in range(tiers):
            tier_type, tier_name = [grab(s).strip('"') for s in data[p:p + 2]]
            tier = Tier(point_tier=(tier_type != 'IntervalTier'))
            p += 2
            tier.xmin, tier.xmax = [float(grab(s)) for s in data[p:p + 2]]
            tier_len = int(grab(data[p + 2]))
            p += 4
            for j in range(tier_len):
                if tier.is_point_tier:
                    x1 = float(grab(data[p]))
                    text = Transcript(grab(data[p + 1]).strip('"'))
                    tier.append(Point(text, x1))
                    p += 3
                else:
                    x0, x1 = [float(grab(s)) for s in data[p:p + 2]]
                    text = Transcript(grab(data[p + 2]).strip('"'))
                    tier.append(Interval(text, x0, x1))
                    p += 4
            self[tier_name] = tier

    def _parse_short(self, data):
        '''Parse SHORT textgrid files. Not intended to be used directly.'''
        self.xmin, self.xmax = [float(s) for s in data[:2]]
        if data[2] != '<exists>':
            return
        tiers = int(data[3])
        p = 4
        for i in range(tiers):
            tier_type, tier_name = [s.strip('"') for s in data[p:p + 2]]
            tier = Tier(point_tier=(tier_type == 'PointTier'))
            tier.xmin, tier.xmax = [float(x) for x in data[p + 2:p + 4]]
            elems = int(data[p + 4])
            p += 5
            for j in range(elems):
                if tier.is_point_tier:
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
            for lineno, line in enumerate(reader):
                if len(line) == 2:
                    text, xpos = line
                    elem = Point(text, float(xpos))
                elif len(line) == 3:
                    text, xmin, xmax = line
                    elem = Interval(text, float(xmin), float(xmax))
                else:
                    raise ValueError('incorrect number of values: file "{}", line {}'.format(csvfile, lineno))
                if not tier:
                    if isinstance(elem, Point):
                        tier = Tier(point_tier=True)
                    else:
                        tier = Tier()
                # The following may raise a TypeError
                tier.append(elem)
        self[tier_name] = tier

    def tier_to_csv(self, tier_name, filename):
        '''Export given tier into a CSV file.

        "tier_name" is the name of the (existing) tier to be exported.
        "filename" is the name of the file.
        '''
        with open(filename, 'w') as csvfile:
            csvfile.write('\n'.join(self[tier_name].to_csv()))

    def write(self, filename, fmt=TEXT_LONG):
        '''Write the text grid into a Praat TextGrid file.

        Obligatory argument "filename" gives the file name.
        Optional argument "formatting" can be TEXT_LONG, TEXT_SHORT, or
        BINARY (see "TextGrid.format()"). Default is TEXT_LONG.
        '''
        global BINARY, TEXT_SHORT, TEXT_LONG
        with open(filename, 'w' if fmt != BINARY else 'wb') as outfile:
            outfile.write(self.format(fmt))
