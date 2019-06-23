#!/usr/bin/env python3
'''textgrids -- Read and handle Praat’s (long) TextGrids

  © Legisign.org, Tommi Nieminen <software@legisign.org>, 2012-19
  Published under GNU General Public License version 3 or newer.

  2019-06-19    r10 A new object layer: Tier. Simple parse error handling.

'''

import codecs
import re
from collections import OrderedDict, namedtuple

version = '10'

class ParseError(Exception):
    def __str__(self):
        return 'Parse error on line {}'.format(self.args[0])

# Point class
Point = namedtuple('Point', ['text', 'xpos'])

class Interval(object):
    '''Interval is a timeframe xmin..xmax labelled "text".'''

    def __init__(self, text=None, xmin=0.0, xmax=0.0):
        self.text = text
        self.xmin = xmin
        self.xmax = xmax
        if self.xmin > self.xmax:
            return ValueError

    def __repr__(self):
        '''Return (semi-)readable representation of self.'''
        return '<Interval text="{}" xmin={} xmax={}>'.format(self.text,
                                                             self.xmin,
                                                             self.xmax)

    @property
    def dur(self):
        '''Return duration.'''
        return self.xmax - self.xmin

    @property
    def mid(self):
        '''Return midpoint in time.'''
        return self.xmin + self.dur / 2

    def timegrid(self, num=3):
        '''Return even-spaced time grid.'''
        if num <= 0 or num != int(num):
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
        if not self.interval_tier:
            raise TypeError
        area = self[first:last]
        if area:
            xmin = self[first].xmin
            xmax = self[last].xmax
            text = ''.join([segm.text for segm in area])
            new_segm = Interval(text, xmin, xmax)
            self = self[first:] + new_segm + self[:last]

    def csv(self):
        '''Return tier data in CSV-like list.'''
        if self.is_point_tier:
            return ['"{}";{}'.format(t, xp) for t, xp in self]
        else:
            return ['"{}";{};{}'.format(t, xb, xe) for t, xb, xe in self]

class TextGrid(OrderedDict):
    '''TextGrid is a dict of tier names (keys) and Tiers (values).'''

    def __init__(self, read_file=None):
        super().__init__({})
        self.filename = read_file
        if self.filename:
            self.read(self.filename)

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
        '''Parse short or long text-mode TextGrids.'''
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
            elif new_interval.match(line):
                tier = Tier()
            elif new_point.match(line):
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
                        tier.append(Point(val, x1))
                    else:
                        tier.append(Interval(val, x0, x1))
        if tier:
            self[name] = tier

    def _parse_short(self, data):
        '''Parse SHORT textgrid files. Not meant to be used directly.'''
        self.xmin, self.xmax = [float(num) for num in data[:2]]
        if data[2] != '<exists>':
            return
        tier = []
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

    def read(self, filename):
        '''Read a file as a TextGrid.'''
        self.filename = filename
        # Praat uses UTF-16 or UTF-8 with no apparent pattern
        try:
            with codecs.open(self.filename, 'r', 'UTF-16') as infile:
                buff = [line.strip() for line in infile]
        except UnicodeError:
            with open(self.filename, 'r') as infile:
                buff = [line.strip() for line in infile]
        self.parse(buff)

    def tier_from_csv(self, tier_name, filename, point_tier=False):
        '''Import CSV file to an interval or point tier.'''
        import csv
        tier = Tier(point_tier=point_tier)
        with open(filename, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            for line in reader:
                if point_tier:
                    text, xpos = line
                    tier.append(Point(text, xpos))
                else:
                    text, xmin, xmax = line
                    tier.append(Interval(text, xmin, xmax))
        self[tier_name] = tier

    def tier_to_csv(self, tier_name, filename):
        '''Export given tier into a CSV file.'''
        with open(filename, 'w') as csvfile:
            csvfile.write('\n'.join(self[tier_name].csv()))

    def write(self, filename):
        '''Write the text grid into a Praat TextGrid file.'''
        with open(filename, 'w') as f:
            f.write(str(self))

# A simple test run
if __name__ == '__main__':
    import sys
    import os.path

    # Error messages
    E_IOERR = 'General I/O error in file "{}"'
    E_NOTFOUND = 'File not found: "{}"'
    E_PARSE = 'Parse error in file "{}", line {}'
    E_PERMS = 'No permission to read file "{}"'

    if len(sys.argv) == 1:
        print('Usage: textgrids FILE...')
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
