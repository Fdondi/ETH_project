# setup.py
from setuptools import setup, find_packages

setup(
    name='myplugin',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'pytest11': [
            'myplugin = myplugin.plugin_module',
        ],
    },
)