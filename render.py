#
# Render a single jinja2 template with the given json data.
#
# Usage: python render.py <key> <data.json> <template.j2> <output>
#

import jinja2
import json
import glob
import sys


key = sys.argv[1]
data = sys.argv[2]
template = sys.argv[3]
output = sys.argv[4]

with open(data) as f:
    context = {key: json.load(f)}
with open(template) as f:
    jinja_template = jinja2.Template(f.read())
rendered = jinja_template.render(context)
with open(output, 'w') as f:
    f.write(rendered)
print('Wrote', output)
