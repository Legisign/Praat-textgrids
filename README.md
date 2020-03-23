# praat-textgrids -- Praat TextGrid manipulation in Python

## Description

`textgrids` is a module for handling Praat TextGrid files in any format (short text, long text, or binary). The module implements five classes, from largest to smallest:

* `TextGrid` -- a `dict` with tier names as keys and `Tier`s as values
* `Tier` -- a `list` of either `Interval` or `Point` objects
* `Interval` -- an `object` representing Praat intervals
* `Point` -- a `namedtuple` representing Praat points
* `Transcript` -- a `str` with special methods for transcription handling

All Praat text objects are represented as `Transcript` objects.

The module also exports the following variables:

* `diacritics` -- a `dict` of all diacritics with their Unicode counterparts
* `inline_diacritics` -- a `dict` of inline (symbol-like) diacritics
* `index_diacritics` -- a `dict` of over/understrike diacritics
* `symbols` -- a `dict` of special Praat symbols with their Unicode counterparts
* `vowels` -- a `list` of all vowels in either Praat or Unicode notation

And the following constants (although they CAN be changed due to Python they SHOULDN’T be changed):

* `BINARY` -- symbolic name for the binary file format
* `TEXT_LONG` -- symbolic name for the long text file format
* `TEXT_SHORT` -- symbolic name for the short text file format
* `version` -- module version as string

## Version

This file documents `praat-textgrids` version 1.3.1.

## Copyright

Copyright © 2019–20 Legisign.org, Tommi Nieminen <software@legisign.org>

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>.

## Module contents

### 0. Module properties

Besides `textgrids.version`, which contains the module version number as string, the module exports the following properties:

#### 0.1. symbols

`symbols` is a `dict` that contains all the Praat special notation symbols (as keys) and their Unicode counterparts (as values).

#### 0.2. vowels

`vowels` is a `list` of all vowel symbols in either Praat notation (e.g., `"\as"`) or in Unicode. It is used by `Interval` methods `containsvowel()` and `startswithvowel()`, so changing it, for example, adding new symbols to it or removing symbols used for other purposes in a specific case, will change how those methods function.

#### 0.3. diacritics, inline_diacritics, and index_diacritics

`diacritics` is a `dict` of all diacritics in Praat notation (as keys) and their Unicode counterparts (as values).

`inline_diacritics` and `index_diacritics` are subsets of `diacritics`. The former are semantically diacritics but appear as inline symbols, the latter are the “true” diacritics (i.e., under- or overstrikes) that need special handling when transcoding.

### 0.4. TEXT_LONG, TEXT_SHORT, BINARY

Symbolic constants specifying different file formats in `TextGrid.format()` and `TextGrid.write()` methods. Internally they are just small integers (0, 1, and 2, respectively). The default format is `TEXT_LONG`.

### 1. TextGrid

`TextGrid` is an `collections.OrderedDict` whose keys are tier names (strings) and values are `Tier` objects. The constructor takes an optional filename argument for easy loading and parsing textgrid files.

#### 1.1. Properties

All the properties of `dict` plus:

* `filename` holds the textgrid filename, if any. `read()` and `write()` methods both set or update it.

#### 1.2. Methods

All the methods of `dict` plus:

* `parse()` -- parse string into a TextGrid
* `read()` -- read (and parse) a TextGrid file
* `tier_from_csv()` -- read a textgrid tier from a CSV file
* `tier_to_csv()` -- write a textgrid tier into a CSV file
* `write()` -- write a TextGrid file

`parse()` takes an obligatory string (or `bytes`) argument which contains textgrid data in any of Praat’s three formats (long text, short text, or binary).

`read()` and `write()` both take an obligatory filename argument.

`write()` can take an optional argument specifying the file format; this can be one of `BINARY` (= `int` 2), `TEXT_LONG` (= `int` 0, the default), or `TEXT_SHORT` (= `int` 1).

`tier_from_csv()` and `tier_to_csv()` both take two obligatory arguments, the tier name and the filename, in that order.

### 2. Tier

`Tier` is a list of either `Interval` or `Point` objects.

**NOTE:** `Tier` only allows adding `Interval` or `Point` objects. Adding anything else or mixing `Interval`s and `Point`s will trigger an exception.

#### 2.2. Properties

All the properties of `list` plus:

* `is_point_tier` -- `bool` `True` for point tier, `False` for interval tier.
* `tier_type` -- `str`, either `"IntervalTier"` or `"PointTier"`

`tier_type` exists principally for the convenience of the formatting functions.

#### 2.3. Methods

All the methods of `list` plus:

* `concat()` -- concatenate intervals
* `to_csv()` -- convert tier data into a CSV-like list

`concat()` concatenates given intervals into one. It takes two arguments, `first=` and `last=`, both of which are integer indexes with the usual Python semantics: 0 stands for the first element, -1 for the last element, these being also the defaults. The function raises a `TypeError` if used with a point tier, and `ValueError` if the parameters do not specify a valid slice. **Note** that this is a function and returns the result instead of modifying the Tier in place.

`to_csv()` returns a CSV-like list. It’s mainly intended to be used from the `TextGrid` level method `tier_to_csv()` but can be called directly if writing to a file is not desired.

### 3. Interval

`Interval` is an `object` class representing one Interval on an IntervalTier.

#### 3.1. Properties

* `dur` -- interval duration (`float`)
* `mid` -- interval midpoint (`float`)
* `text` -- text label (`Transcript`)
* `xmax` -- interval end time (`float`)
* `xmin` -- interval start time (`float`)

#### 3.3. Methods

* `containsvowel()` -- does the interval contain a vowel?
* `endswithvowel()` -- does the interval end with a vowel?
* `startswithvowel()` -- does the interval start with a vowel?
* `timegrid()` -- create a time grid

`containsvowel()`, `endswithvowel()`, and `startswithvowel()` are `bool` functions. They check for possible vowels in the `text` property in both Praat notation and Unicode, but can of course make an error if symbols are used in an unexpected way. They don’t take arguments. (Internally, `endswithvowel()` first transcodes the text to IPA removing all diacritics to simplify the test.)

`timegrid()` returns a list of timepoints (in `float`) evenly distributed from `xmin` to `xmax`. It takes an optional integer argument specifying the number of timepoints desired; the default is 3. It raises a `ValueError` if the argument is not an integer or is less than 1.

### 4. Point

`Point` is a `namedtuple` representing one Point on a PointTier.

#### 4.1. Properties

* `text` -- text label (`Transcript`)
* `xpos` -- temporal position (`float`)

### 5. Transcript

`Transcript` is a `str`-derived class with one special method: `transcode()`.

### 5.1. Properties

All the properties of `str`.

#### 5.2. Methods

All the methods of `str` plus:

* `transcode()` -- convert Praat notation to Unicode or vice versa.

Without arguments, `transcode()` assumes its input to be in Praat notation and converts it to Unicode; no check is made as to whether the input really is in Praat notation but nothing **should** happen if it isn’t. User should take care and handle any exceptions.

Optional `to_unicode=False` argument inverts the direction of the transcoding from Unicode to Praat. Again, it is not checked whether input is in Unicode.

With optional `retain_diacritics=True` argument the transcoding does not remove over- and understrike diacritics from the result.

## Examples

### Snippet 1: list syllable durations

    import sys
    import textgrids

    for arg in sys.argv[1:]:
        # Try to open the file as textgrid
        try:
            grid = textgrids.TextGrid(arg)
        # Discard and try the next one
        except:
            continue

        # Assume "syllables" is the name of the tier
        # containing syllable information
        for syll in grid['syllables']:
            # Convert Praat to Unicode in the label
            label = syll.text.transcode()
            # Print label and syllable duration, CSV-like
            print('"{}";{}'.format(label, syll.dur))

### Snippet 2: convert any textgrid to binary format

    import sys
    import os.path
    import textgrids

    for arg in sys.argv[1:]:
        name, ext = os.path.splitext(arg)
        try:
            grid = textgrids.TextGrid(arg)
        except (textgrids.ParseError, textgrids.BinaryError):
            print('Not a recognized file format!', file=sys.stderr)
            continue

        # Write a new file
        grid.write(name + '.bin', fmt=textgrids.BINARY)
