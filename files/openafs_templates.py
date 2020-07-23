# Email templates for nightly linux-rc builders.
body = '''\
The buildbot has detected a {{ status_detected }} on builder {{ buildername }} while building {{ (build['properties'].get('branch', ['unknown']))[0] }}

Build Reason: {{ build['properties'].get('reason', ["<unknown>"])[0] }}

{{ summary }}

Full details are available at:
    {{ build_url }}

The OpenAFS Buildbot,
{{ buildbot_url }}
'''

