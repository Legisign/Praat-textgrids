'''transcript.py -- Praat-to-Unicode transcription conversions

  A str-derived class for handling Praat-to-Unicode and Unicode-to-Praat
  transcription conversions.

  2019-07-11    Separated from textgrids module.
  2019-08-04    Corrected "unrounded open back" symbol.

'''

# Global variables

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
           r'\as': '\u0251',        # unrounded open back
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
                r'\hj': '\u0267'})  # rounded postalveolar-velar fricative

inline_diacritics = {r'\:f': '\u02d0',      # length mark
                     r'\.f': '\u02d1',      # half-length mark
                     r"\'1": '\u02c8',      # primary stress
                     r"\'2": '\u02cc',      # secondary stress
                     r'\|f': '|',           # “phonetic stroke”
                     r'\cn': '\u031a',      # unreleased
                     r'\er': '\u02de'}      # rhotic

index_diacritics = {r'\|v': '\u0329',     # syllabic (under)
                    r'\0v': '\u0325',     # voiceless (under)
                    r'\Tv': '\u031e',     # lowered (under)
                    r'\T^': '\u031d',     # raised (under)
                    r'\T(': '\u0318',     # ATR (under)
                    r'\T)': '\u0319',     # RTR (under)
                    r'\-v': '\u0320',     # backed (under)
                    r'\+v': '\u031f',     # fronted (under)
                    r'\:v': '\u0324',     # breathy voiced (under)
                    r'\~v': '\u0330',     # creaky voiced (under)
                    r'\Nv': '\u032a',     # dental (under)
                    r'\Uv': '\u033a',     # apical (under)
                    r'\Dv': '\u033b',     # laminal (under)
                    r'\nv': '\u032f',     # nonsyllabic (under)
                    r'\3v': '\u0339',     # slightly rounded (under)
                    r'\cv': '\u031c',     # slightly unrounded (under)
                    r'\0^': '\u030a',     # voiceless (over)
                    r"\'^": '\u0301',     # high tone (over)
                    r'\`^': '\u0300',     # low tone (over)
                    r'\-^': '\u0304',     # mid tone (over)
                    r'\~^': '\u0303',     # nasalized (over)
                    r'\v^': '\u030c',     # rising tone (over)
                    r'\^^': '\u0302',     # falling tone (over)
                    r'\:^': '\u0308',     # centralized (over)
                    r'\N^': '\u0306',     # short (over)
                    r'\li': '\u0361'}     # simultaneous articulation (over)

# There’s a neater way of combining dicts in Python 3.5+,
# but we can’t assume the user has that
diacritics = inline_diacritics.copy()
diacritics.update(index_diacritics)

class Transcript(str):
    '''String class with an extra method for notation transcoding.'''

    def transcode(self, to_unicode=True, retain_diacritics=False):
        '''Provide Praat-to-Unicode and Unicode-to-Praat transcoding.

        Unless to_unicode is False, Praat-to-Unicode is assumed, otherwise
        Unicode-to-Praat.

        If retain_diacritics is False (the default), removes over/understrike
        (i.e., “index”) diacritics (usually best practice for graphs).
        '''
        global symbols, inline_diacritics, index_diacritics

        out = str(self)

        # First stage (only when Unicode-to-Praat): if retaining
        # index diacritics, swap them to follow their symbols,
        # otherwise remove them
        if not to_unicode:
            # print('in = "{}"'.format([c for c in out]))
            if retain_diacritics:
                for uni in index_diacritics.values():
                    p = out.find(uni)
                    while p >= 0:
                        out = out[:p] + out[p + 1] + out[p] + out[p + 2:]
                        p = out.find(uni, p + 2)
                        # print('mid = "{}'.format([c for c in out]))
            else:
                for uni in index_diacritics.values():
                    out = out.replace(uni, '')
            # print('out = "{}"'.format([c for c in out]))

        # Second stage: change INLINE symbols (diacritics included)
        # (there’s a neater way of combining dicts in Python 3.5+,
        # but we can’t assume the user has that)
        inline_symbols = symbols.copy()
        inline_symbols.update(inline_diacritics)
        for praat, uni in inline_symbols.items():
            if to_unicode:
                out = out.replace(praat, uni)
            else:
                out = out.replace(uni, praat)

        # Third stage (only when Praat-to-Unicode and retaining diacritics):
        # swap the index diacritics to precede their symbols
        if to_unicode and retain_diacritics:
            for praat in index_diacritics:
                p = 0
                while out.find(praat, p) > 0:
                    p = out.index('\\')
                    out = out[:p - 1] + \
                          index_diacritics[out[p:p + 3]] + \
                          out[p - 1] + \
                          out[p + 3:]
                    p += 2

        # Fourth stage: change index diacritics
        # (unless already removed in the first stage)
        for praat, uni in index_diacritics.items():
            if to_unicode:
                out = out.replace(praat, uni if retain_diacritics else '')
            elif retain_diacritics:
                out = out.replace(uni, praat)

        return out
