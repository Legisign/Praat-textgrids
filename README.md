# textgrids module

''textgrids'' is a module for handling Praat short or long text-file TextGrid files. It implements four classes: TextGrid, Tier, Interval, and Point.

## TextGrid

TextGrid is a dict whose keys are tier names (strings) and values are Tier objects.

### Differences from standard dict

Three special methods: ''parse()'', ''read()'', and ''write()''.

### TextGrid properties

No special properties.

### TextGrid methods

parse(data) -- parse string ''data'' into a TextGrid
read(name) -- read a TextGrid file ''name''
write(name) -- write a TextGrid file ''name''

## Tier

Tier is a list of either Interval or Point objects.

### Differences from standard list

Tier only allows adding Interval or Point objects, and not mixing those. There is one special property, ''is_point_tier'', and two special methods, ''concat()'' and ''to_csv()''.

### Tier properties

is_point_tier -- Boolean value: True for point tier, False for interval tier.

### Tier methods

concat(first, last) -- concatenate intervals first..last, inclusive
to_csv() -- convert tier data to CSV

## Interval

Interval is an namedtuple-like object.

### Interval properties

dur -- interval duration (for convenience)
mid -- interval midpoint (for convenience)
text -- text label (can be in Praat notation)
xmax -- interval end time
xmin -- interval start time

### Interval methods

timegrid(num) -- create a grid of ''num'' time slices (for convenience)

## Point

Point is a namedtuple with two properties, ''text'' and ''xpos''.

### Point properties

text -- text label
xpos -- temporal position
