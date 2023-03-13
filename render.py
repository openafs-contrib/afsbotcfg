#
# Render a single jinja2 template with the given json data.
#
# Usage: python render.py <key> <data.json> <template.j2> <output>
#

import jinja2
import json
import glob
import sys


data = sys.argv[1]
template = sys.argv[2]
output = sys.argv[3]

with open(data) as f:
    context = json.load(f)
with open(template) as f:
    jinja_template = jinja2.Template(f.read())
rendered = jinja_template.render(context)
with open(output, 'w') as f:
    f.write(rendered)
print('Wrote', output)
