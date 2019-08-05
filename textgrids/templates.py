'''

  templates.py

  2019-07-15    Done.
  2019-08-02    Bug fix. Always TEXT_{LONG|SHORT}, never
                {LONG|SHORT}_TEXT.
  2019-08-04    Bug fix (line breaks, indentation in templates).

'''

# Symbolic names for the formats

TEXT_LONG = 0
TEXT_SHORT = 1
BINARY = 2

# Formatting templates

long_header = '''File type = "ooTextFile"
Object class = "TextGrid"

xmin = {}
xmax = {}
tiers? <exists>
size = {}
item []:'''

short_header = '''File type = "ooTextFile"
Object class = "TextGrid"

{xmin}
{xmax}
<exists>
{length}
'''

long_tier = '''
    item [{}]:
        class = "{}"
        name = "{}"
        xmin = {}
        xmax = {}
        {}: size = {}'''

short_tier = '''"{tier_type}"
"{name}"
{xmin}
{xmax}
{length}
'''

long_point = '''
            points [{}]:
                xpos = {}
                text = "{}"'''

short_point = '''{xpos}
"{text}"
'''

long_interval = '''
            intervals [{}]:
                xmin = {}
                xmax = {}
                text = "{}"'''

short_interval = '''{xmin}
{xmax}
"{text}"
'''
