import setuptools
import re


def read_version():
    with open('afsbotcfg/__init__.py') as f:
        contents = f.read()
    m = re.match(r"__version__\s*=\s*'(.*)'", contents)
    if m:
        version = m.group(1)
    else:
        version = '0.0.0'
    return version


setuptools.setup(
    name='afsbotcfg',
    version=read_version(),
    description='Buildbot extensions for OpenAFS',
    packages=['afsbotcfg'],
    install_requires=[],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
