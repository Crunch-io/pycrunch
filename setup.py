#!/usr/bin/env python
# coding: utf-8

import os
import io
import re
import sys

thisdir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(thisdir, 'pycrunch', 'version.py')) as v_file:
    VERSION = re.compile(
        r".*__version__ = '(.*?)'",
        re.S).match(v_file.read()).group(1)

from setuptools import setup, find_packages

def get_long_desc():
    root_dir = os.path.dirname(__file__)
    if not root_dir:
        root_dir = '.'
    readme_fn = os.path.join(root_dir, 'README.md')
    with io.open(readme_fn, encoding='utf-8') as stream:
        return stream.read()

needs_pytest = {'pytest', 'test'}.intersection(sys.argv)
pytest_runner = ['pytest_runner'] if needs_pytest else []

setup_params = dict(
    name='pycrunch',
    version=VERSION,
    description="Crunch.io Client Library",
    long_description=get_long_desc(),
    url='https://github.com/Crunch-io/pycrunch',
    download_url='https://github.com/Crunch-io/pycrunch/archive/master.zip',

    classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    author=u'Crunch.io',
    author_email='dev@crunch.io',
    license='LGPL',
    install_requires=[
        'requests>=2.3.0',
        'six',
    ],
    tests_require=[
        'pandas',
        'pytest',
        'mock'
    ],
    setup_requires=[
    ] + pytest_runner,
    packages=find_packages(),
    namespace_packages=[],
    include_package_data=True,
    package_data={
        'pycrunch': ['*.json', '*.csv']
    },
    extras_require={
        'pandas': ['pandas']
    },
    zip_safe=True,
    entry_points={},
)

if __name__ == '__main__':
    setup(**setup_params)
