# OpenAFS Buildbot master site specific settings.

title = '{{ afsbotcfg_title }}'
repo = '{{ afsbotcfg_repo }}'
buildbotURL = '{{ afsbotcfg_url }}'
www_port = {{ afsbotcfg_www_port }}
build_delay = {{ afsbotcfg_build_delay | d(120) }}
{% if afsbotcfg_limit_gerrit_builders is undefined %}
limit_gerrit_builders = None
{% else %}
limit_gerrit_builders = [
{% for name in afsbotcfg_limit_gerrit_builders %}
    '{{ name }}',
{% endfor %}
]
{% endif %}
