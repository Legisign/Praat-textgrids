# Praat-textgrids

`textgrids` is a module for handling Praat short or long text-file TextGrid files. It implements five classes. From largest to smallest:

* `TextGrid` -- a `dict` with tier names as keys and `Tier`s as values
* `Tier` -- a `list` of either `Interval` or `Point` objects
* `Interval` -- an `object` representing Praat intervals
* `Point` -- a `namedtuple` representing Praat points
* `Transcript` -- a `str` with special methods for transcription handling

All Praat text objects are represented as `Transcript` objects.

## TextGrid

`TextGrid` is a `dict` whose keys are tier names (strings) and values are `Tier` objects.

### TextGrid properties

All the properties of `dict`s plus:

* `filename` holds the textgrid filename, if any. `read()` and `write()` methods both set or update it.

### TextGrid methods

All the methods of `dict`s plus:

* `parse()` -- parse string `data` into a TextGrid
* `read()` -- read a TextGrid file `name`
* `write()` -- write a TextGrid file `name`
* `tier_from_csv()` -- read a textgrid tier from a CSV file
* `tier_to_csv()` -- write a textgrid tier into a CSV file

## Tier

`Tier` is a list of either `Interval` or `Point` objects.

### Note

`Tier` only allows adding `Interval` or `Point` objects, and not mixing those.

### Tier properties

All the properties of `list`s plus:

* `is_point_tier` -- Boolean value: `True` for point tier, `False` for interval tier.

### Tier methods

All the methods of `list`s plus:

* `concat()` -- concatenate intervals
* `to_csv()` -- convert tier data into a CSV-like list

`concat()` returns a `TypeError` if used with a point tier.

## Interval

`Interval` is an `object` class.

### Interval properties

* `dur` -- interval duration (`float`)
* `mid` -- interval midpoint (`float`)
* `text` -- text label (`Transcript`)
* `xmax` -- interval end time (`float`)
* `xmin` -- interval start time (`float`)

### Interval methods

* `containsvowel()` -- Boolean: does the interval contain a vowel?
* `startswithvowel()` -- Boolean: does the interval start with a vowel?
* `timegrid()` -- create a grid of even time slices

`containsvowel()` and `startswithvowel()` check for possible vowels in both Praat notation and Unicode but can of course make an error if symbols are used in an unexpected way.

## Point

`Point` is a `namedtuple` with two properties, `text` and `xpos`.

### Point properties

* `text` -- text label (`Transcript`)
* `xpos` -- temporal position (`float`)

## Transcode

`Transcode` is a `str` with one special method.

### Transcode properties

All the properties of `str`s.

### Transcode methods

All the methods of `str`s plus:

* `transcode()` -- convert Praat notation to Unicode or vice versa.
