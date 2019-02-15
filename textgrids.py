#!/usr/bin/env python3
'''textgrids -- Read and handle Praat’s (long) TextGrids

  Author :  Tommi Nieminen <software@legisign.org>
  License:  GNU General Public License version 3 or newer

  2016-02-15    1.2.0   Finally beginning to handle point tiers.
  2018-01-15    1.3.0   Back to the project.
  2018-04-06    1.4.0   Added selection of tier(s) to print in __main__().

'''

import codecs
import re
from collections import OrderedDict, namedtuple

version = '1.4.0'

# Known keys in different contexts (constant)
known_keys = {
    'type': ('File type', 'Object class'),
    'header': ('xmin', 'xmax', 'size'),
    'item': ('class', 'name', 'xmin', 'xmax', 'intervals: size'),
    'intervals': ('xmin', 'xmax', 'text')
}

# New types (intervals, points)
Interval = namedtuple('Interval', ['text', 'xmin', 'xmax'])
Point = namedtuple('Point', ['text', 'xpos'])

class ParseError(Exception):
    pass

def _keyval(s, checklist=None):
    '''Handy key–value type conversions.'''
    keyval = re.compile('^\s*(.+)\s+=\s+(.+)$')
    key, val = keyval.match(s).groups()
    if checklist and key not in checklist:
        print('Unexpected key: "{}"'.format(key))
        raise ParseError('Unexpected key: "{}"'.format(key))
    elif val.startswith('"'):
        val = val.strip('"')
    else:
        # Sometimes int() would be more efficient, but Praat doesn’t
        # make the difference
        val = float(val)
    return key, val

def _readtobuffer(stream):
    '''Read a stream into a buffer.

    Replace with a more robust algorithm if you’re having problems.'''
    return [line.strip() for line in stream]

class TextGrid(OrderedDict):
    '''TextGrid is a dictionary of tier where tier names are keys.

    Tiers are simple lists that contain either Interval or Point objects.
    '''
    def __init__(self, inputfile=None):
        super().__init__({})
        if inputfile:
            self.read(inputfile)
        else:
            self.filename = None

    def __repr__(self):
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
        beg = tier[first].xmin
        end = tier[last].xmax
        text = ' '.join([segm.text for segm in area])
        new_segm = Interval(text=text, xmin=beg, xmax=end)
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
        '''A state grammar parser for the TextGrid data.'''
        global known_keys
        for line in data[0:2]:
            line = line.strip()
            key, val = _keyval(line, checklist=known_keys['type'])
        mode = 'header'
        for line in data[2:]:
            line = line.strip()
            if not line:
                pass
            elif line.startswith('item'):
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
                    # Note: the variables now point to the same list
                    # (to simplify references)
                    #tier = self[val] = []
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

    def die(msg):
        print('{}: {}'.format(os.path.basename(sys.argv[0]), msg),
              file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) == 1:
        print('Usage: textgrids FILE...')
    tiers = []
    for arg in sys.argv[1:]:
        if not arg.endswith('.TextGrid'):
            tiers.append(arg)
        else:
            try:
                textgrid = TextGrid(arg)
            except ParseError:
                die('Invalid or not a textgrid: {}'.format(arg))
                continue
            print('"{}"'.format(textgrid.filename))
            if tiers:
                for tier in tiers:
                    if tier not in textgrid:
                        die('Ei tasoa "{}" tiedostossa "{}"'.format(tier, textgrid.filename))
                    print('\n'.join(textgrid.csv(tier)))
            else:
                for tier in textgrid:
                    print('\n'.join(textgrid.csv(tier)))
            tiers = []
