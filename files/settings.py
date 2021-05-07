# OpenAFS Buildbot master site specific settings.

buildbotURL = '{{ buildbot_master_url }}'
www_port = {{ buildbot_master_www_port }}
{% if afsbotcfg_limit_gerrit_builders is undefined %}
limit_gerrit_builders = None
{% else %}
limit_gerrit_builders = [
{% for name in afsbotcfg_limit_gerrit_builders %}
    '{{ name }}',
{% endfor %}
]
{% endif %}
