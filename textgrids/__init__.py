#!/usr/bin/env python3
'''textgrids -- Read and handle Praat’s (long) TextGrids

  © Legisign.org, Tommi Nieminen <software@legisign.org>, 2012-19
  Published under GNU General Public License version 3 or newer.

  2019-07-01  1.0.3   More verbose docstrings. Removed optional argument from
                      TextGrid.tier_from_csv().

'''

import codecs
import re
from collections import OrderedDict, namedtuple

version = '1.0.3'

# Global variable: Praat-to-Unicode character mappings

# Symbol table
# (only vowels are added first in order to get the ’vowels’ variable)
symbols = {r'\i-': '\u0268',        # unrounded close central
           r'\u-': '\u0289',        # rounded close central
           r'\mt': '\u026f',        # unrounded close back
           r'\ic': '\u026a',        # unrounded close lax front
           r'\yc': '\u028f',        # rounded close lax front
           r'\hs': '\u028a',        # rounded close lax back
           r'\o/': 'ø',             # rounded close-mid front
           r'\e-': '\u0258',        # unrounded close-mid central
           r'\o-': '\u0275',        # rounded close-mid central
           r'\rh': '\u0264',        # unrounded close-mid back
           r'\sw': '\u0259',        # neutral vowel, schwa
           r'\ef': 'ɛ',             # unrounded open-mid front
           r'\oe': 'œ',             # rounded open-mid front
           r'\er': '\u025c',        # unrounded open-mid central
           r'\kb': '\u025e',        # rounded open-mid central
           r'\vt': '\u028c',        # unrounded open-mid back
           r'\ct': '\u0254',        # rounded open-mid back
           r'\ae': 'æ',             # unrounded nearly open back
           r'\at': '\u0250',        # unrounded open central
           r'\Oe': '\u0276',        # rounded open front
           r'\as': '\u03b1',        # unrounded open back
           r'\ab': '\u0252'}        # rounded open back

# Vowels in either notation
vowels = list('aeiouyæø') + list(symbols.keys()) + list(symbols.values())

# Now add the consonants AND in-line diacritics
symbols.update({r'\t.': '\u0288',   # voiceless retroflex plosive
                r'\?-': '\u02a1',   # voiceless epiglottal plosive
                r'\?g': '\u0294',   # voiceless glottal plosive
                r'\d.': '\u0256',   # voiced retroflex plosive
                r'\j-': '\u025f',   # voiced palatal plosive
                r'\gs': '\u0261',   # voiced velar plosive
                r'\gc': '\u0262',   # voiced uvular plosive
                r'\mj': '\u0271',   # voiced labiodental nasal
                r'\n.': '\u0273',   # voiced retroflex nasal
                r'\ng': 'ŋ',        # voiced velar nasal
                r'\nc': '\u0274',   # voiced uvular nasal
                r'\ff': '\u0278',   # voiced bilabial fricative
                r'\tf': '\u019f',   # voiceless dental fricative
                r'\l-': '\u026c',   # voiceless alveolodental fricative
                r'\sh': '\u0283',   # voiceless postalveolar fricative
                r'\s.': '\u0282',   # voiceless retroflex fricative
                r'\cc': '\u0255',   # voiceless alveolopalatal fricative
                r'\c,': 'ç',        # voiceless palatal fricative
                r'\wt': '\u028d',   # voiceless labiovelar fricative
                r'\cf': '\u03c7',   # voiceless uvular fricative
                r'\h-': '\u0127',   # voiceless pharyngeal fricative
                r'\hc': '\u029c',   # voiceless epiglottal fricative
                r'\bf': '\u03b2',   # voiced bilabial fricative
                r'\dh': '\u00f0',   # voiced dental fricative
                r'\lz': '\u026e',   # voiced lateral fricative
                r'\zh': '\u0292',   # voiced postalveolar fricative
                r'\z.': '\u0290',   # voiced retroflex fricative
                r'\zc': '\u0291',   # voiced alveolopalatal fricative
                r'\jc': '\u029d',   # voiced palatal fricative
                r'\gf': '\u0263',   # voiced velar fricative
                r'\ri': '\u0281',   # voiced uvular fricative
                r'\9e': '\u0295',   # voiced pharyngeal fricative
                r'\9-': '\u02a2',   # voiced epiglottal fricative
                r'\h^': '\u0266',   # voiced glottal fricative
                r'\vs': '\u028b',   # voiced labiodental approximant
                r'\rt': '\u0279',   # voiced alveolar approximant
                r'\r.': '\u027b',   # voiced retroflex approximant
                r'\ht': '\u0265',   # voiced labial-palatal approximant
                r'\ml': '\u0270',   # voiced velar approximant
                r'\bc': '\u0299',   # voiced bilabial trill
                r'\rc': '\u0280',   # voiced uvular trill
                r'\fh': '\u027e',   # voiced alveolar tap
                r'\rl': '\u027a',   # voiced lateral flap
                r'\f.': '\u027d',   # voiced retroflex flap
                r'\l.': '\u026d',   # voiced retroflex lateral
                r'\yt': '\u028e',   # voiced lateral approximant
                r'\lc': '\u029f',   # voiced velar lateral approximant
                r'\b^': '\u0253',   # bilabial implosive stop
                r'\d^': '\u0257',   # alveolar implosive stop
                r'\j^': '\u0284',   # palatal implosive stop
                r'\g^': '\u0260',   # velar implosive stop
                r'\G^': '\u029b',   # uvular implosive stop
                r'\O.': '\u0298',   # bilabial click
                r'\|1': '\u01c0',   # dental click
                r'\|2': '\u01c1',   # lateral click
                r'\|-': '\u01c2',   # palatoalveolar click
                r'\l~': '\u026b',   # velarized voiced alveolar lateral appr.
                r'\hj': '\u0267',   # rounded postalveolar-velar fricative
                r'\:f': '\u02d0',   # length mark
                r'\.f': '\u02d1',   # half-length mark
                r"\'1": '\u02c8',   # primary stress
                r"\'2": '\u02cc',   # secondary stress
                r'\|f': '|',        # “phonetic stroke”
                r'\cn': '\u031a',   # unreleased
                r'\er': '\u02de'})  # rhotic

# Diacritics include only over- and understrikes---
# no need to handle in-line symbols
diacritics = {r'\|v': '\u0329',     # syllabic (understrike)
              r'\0v': '\u0325',     # voiceless (understrike)
              r'\Tv': '\u031e',     # lowered (understrike)
              r'\T^': '',           # raised (understrike)
              r'\T(': '\u0318',     # ATR (understrike)
              r'\T)': '\u0319',     # RTR (understrike)
              r'\-v': '\u0320',     # backed (understrike)
              r'\+v': '\u031f',     # fronted (understrike)
              r'\:v': '\u0324',     # breathy voiced (understrike)
              r'\~v': '\u0330',     # creaky voiced (understrike)
              r'\Nv': '\u032a',     # dental (understrike)
              r'\Uv': '\u033a',     # apical (understrike)
              r'\Dv': '\u033b',     # laminal (understrike)
              r'\nv': '\u032f',     # nonsyllabic (understrike)
              r'\3v': '\u0339',     # slightly rounded (understrike)
              r'\cv': '\u031c',     # slightly unrounded (understrike)
              r'\0^': '\u030a',     # voiceless (overstrike)
              r"\'^": '\u0301',     # high tone (overstrike)
              r'\`^': '\u0300',     # low tone (overstrike)
              r'\-^': '\u0304',     # mid tone (overstrike)
              r'\~^': '\u0303',     # nasalized (overstrike)
              r'\v^': '\u030c',     # rising tone (overstrike)
              r'\^^': '\u0302',     # falling tone (overstrike)
              r'\:^': '\u0308',     # centralized (overstrike)
              r'\N^': '\u0306',     # short (overstrike)
              r'\li': '\u0361'}     # simultaneous articulation (overstrike)

class ParseError(Exception):
    def __str__(self):
        return 'Parse error on line {}'.format(self.args[0])

class Transcript(str):
    '''String class with an extra method for notation transcoding.'''

    def transcode(self, to_unicode=True, retain_diacritics=False):
        '''Provide Praat-to-Unicode and Unicode-to-Praat transcoding.

        Unless to_unicode is False, Praat-to-Unicode is assumed.
        By default removes diacritics (usually best practice for pictures).
        '''
        global symbols, diacritics
        out = str(self)
        for key, val in symbols.items():
            if to_unicode and (key in out):
                out = out.replace(key, val)
            elif (not to_unicode) and (val in out):
                out = out.replace(val, key)
        for key, val in diacritics.items():
            if not retain_diacritics:
                val = ''
            out = out.replace(key, val)
        return out

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
        '''Parse short or long text-mode TextGrids.

        Obligatory argument "data" is a string.
        '''
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
        '''Read given file as a TextGrid.

        "filename" is the name of the file.
        '''
        self.filename = filename
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
