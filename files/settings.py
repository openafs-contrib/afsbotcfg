# OpenAFS Buildbot master site specific settings.

title = '{{ afsbotcfg_title }}'
buildbotURL = '{{ afsbotcfg_url }}'
www_port = {{ afsbotcfg_www_port }}
{% if afsbotcfg_limit_gerrit_builders is undefined %}
limit_gerrit_builders = None
{% else %}
limit_gerrit_builders = [
{% for name in afsbotcfg_limit_gerrit_builders %}
    '{{ name }}',
{% endfor %}
]
{% endif %}
