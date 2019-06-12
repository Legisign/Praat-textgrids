#!/usr/bin/env python3
'''textgrids -- Read and handle Praat’s (long) TextGrids

  © Legisign.org, Tommi Nieminen <software@legisign.org>, 2012-19
  Published under GNU General Public License version 3 or newer

  2019-06-12    r7  Finally a parser for short-form textgrids. Long-form
                    may be unfunctional for a while now :)

'''

import codecs
import re
from collections import OrderedDict, namedtuple

version = '7'

# Known keys in different contexts (constant)
known_keys = {
    'type': ('File type', 'Object class'),
    'header': ('xmin', 'xmax', 'size'),
    'item': ('class', 'name', 'xmin', 'xmax', 'intervals: size'),
    'intervals': ('xmin', 'xmax', 'text')
}

# Point type
Point = namedtuple('Point', ['text', 'xpos'])

class ParseError(Exception):
    pass

def _keyval(s, checklist=None):
    '''Handy key–value type conversions.'''
    keyval = re.compile('^\s*(.+)\s+=\s+(.+)$')
    key, val = keyval.match(s).groups()
    if checklist and key not in checklist:
        # print('Unexpected key: "{}"'.format(key))
        raise ParseError('Unexpected key: "{}"'.format(key))
    elif val.startswith('"'):
        val = val.strip('"')
    else:
        val = float(val)
    return key, val

def _readtobuffer(stream):
    '''Read a stream into a buffer.

    Replace with a more robust algorithm if you’re having problems.'''
    return [line.strip() for line in stream]

class Interval(object):
    '''Interval is a timeframe between xmin and xmax with label text.'''
    def __init__(self, text=None, xmin=0.0, xmax=0.0):
        self.text = text
        self.xmin = xmin
        self.xmax = xmax

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

class TextGrid(OrderedDict):
    '''TextGrid is a dictionary of tier where tier names are keys.

    Tiers are simple lists that contain either Interval or Point objects.
    '''
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

    def concat(self, tier_name, first=0, last=-1):
        '''Concatenate given segments on given tier.'''
        tier = self[tier_name]
        area = tier[first:last]
        xmin = tier[first].xmin
        xmax = tier[last].xmax
        text = ''.join([segm.text for segm in area])
        new_segm = Interval(text=text, xmin=xmin, xmax=xmax)
        tier = tier[first:] + new_segm + tier[:last]

    def csv(self, tier):
        '''Return tier in a CSV-like list.'''
        return ['"{}";{};{}'.format(text, xmin, xmax) \
                for text, xmin, xmax in self[tier]]

    def export(self, csvfile):
        '''Export textgrid to a CSV file.'''
        with open(csvfile, 'w') as f:
            for tier in self:
                f.write('\n'.join(self.csv(tier)))

    def parse(self, data):
        '''Parse short or long text-mode TextGrids.'''
        filetype, objclass, separ = data[:3]
        if filetype != 'File type = "ooTextFile"' or \
           objclass != 'Object class = "TextGrid"' or \
           separ != '':
           raise ValueError
        if re.match('^-?\d+.?\d*$', data[3]):
            self._parse_short(data[3:])
        else:
            self._parse_long(data[3:])

    def _parse_long(self, data):
        '''Parse LONG textgrid files. Not meant to be used directly.'''
        mode = 'header'
        for line in data:
            if line.startswith('item'):
                mode = 'item'
            elif line.startswith('intervals '):
                mode = 'interval'
            elif line.startswith('point '):
                mode = 'point'
            elif mode == 'header' and not line.startswith('tiers?'):
                key, val = _keyval(line, checklist=known_keys['header'])
                if key == 'xmin':
                    self.xmin = val
                elif key == 'xmax':
                    self.xmax = val
            elif mode == 'item':
                key, val = _keyval(line, checklist=known_keys['item'])
                if key == 'name':
                    # Note: same list, just to simplify refs
                    tier = self[val] = []
            elif mode == 'interval':
                key, val = _keyval(line, checklist=known_keys['intervals'])
                if key == 'xmin':
                    xmin = val
                elif key == 'xmax':
                    xmax = val
                else:
                    tier.append(Interval(text=val, xmin=xmin, xmax=xmax))
            elif mode == 'point':
                key, val = _keyval(line, checklist=known_keys['points'])
                if key == 'xpos':
                    xpos = val
                else:
                    tier.append(Point(text=val, xpos=xpos))

    def _parse_short(self, data):
        '''Parse SHORT textgrid files. Not meant to be used directly.'''
        gmin, gmax = [float(num) for num in data[:2]]
        print('gmin={}, gmax={}'.format(gmin, gmax))
        if data[2] != '<exists>':
            return
        tier = []
        mode = 'type'
        for line in data[4:]:
            print('PARS[{}] :: "{}"'.format(mode, line))
            if mode == 'type':
                typ = 'interval' if line == '"IntervalTier"' else 'point'
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
                mode = 'xmin' if typ == 'interval' else 'xmop'
            elif mode == 'xmin':
                x0 = float(line)
                mode = 'xmop'
            elif mode == 'xmop':
                x1 = float(line)
                mode = 'text'
            elif mode == 'text':
                if typ == 'interval':
                    tier.append(Interval(line.strip('"') , x0, x1))
                else:
                    tier.append(Point(line.strip('"'), x1))
                if len(tier) == tlen:
                    self[name] = tier
                    name = None
                    tier = []
                    mode = 'type'
                else:
                    mode = 'xmin'

    def read(self, filename):
        '''Read a file as a TextGrid.'''
        self.filename = filename
        # Praat uses UTF-16 or UTF-8 with no apparent pattern
        try:
            with codecs.open(self.filename, 'r', 'UTF-16') as f:
                buff = _readtobuffer(f)
        except UnicodeError:
            with open(self.filename, 'r') as f:
                buff = _readtobuffer(f)
        self.parse(buff)

    def write(self, filename):
        '''Write the text grid into a Praat TextGrid file.'''
        with open(filename, 'w') as f:
            f.write(str(self))

# A simple test run
if __name__ == '__main__':
    import sys
    import os.path

    # Error messages
    INVALID_TEXTGRID = 'ERROR: invalid textgrid or not a textgrid: "{}"'
    TIER_NOT_FOUND = 'ERROR: no tier "{}" in file "{}"'

    def die(msg):
        print('{}: {}'.format(os.path.basename(sys.argv[0]), msg),
              file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) == 1:
        print('USAGE: textgrids FILE...')
    for arg in sys.argv[1:]:
        try:
            textgrid = TextGrid(arg)
        except ParseError:
            die(INVALID_TEXTGRID.format(arg))
            continue
        # Print in long format
        print(textgrid)
