#!/usr/bin/env python
# coding: utf-8

import os
import io
import re
from setuptools import setup, find_packages

thisdir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(thisdir, 'src', 'pycrunch', 'version.py')) as v_file:
    VERSION = re.compile(
        r".*__version__ = '(.*?)'",
        re.S).match(v_file.read()).group(1)


def get_long_desc():
    readme_fn = os.path.join(thisdir, 'README.md')
    with io.open(readme_fn, encoding='utf-8') as stream:
        return stream.read()


requires = [
    'requests>=2.14.0',
    'six',
]

tests_requires = [
    'mock',
    'pytest',
    'pytest-cov',
]

setup_params = dict(
    name='pycrunch',
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*',
    version=VERSION,
    description="Crunch.io Client Library",
    long_description=get_long_desc(),
    url='https://github.com/Crunch-io/pycrunch',
    classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    author=u'Crunch.io',
    author_email='dev@crunch.io',
    license='LGPL',
    install_requires=requires,
    tests_require=tests_requires,
    packages=find_packages('src', exclude=['tests']),
    package_dir={'': 'src'},
    include_package_data=True,
    extras_require={
        'pandas:python_version=="3.4"': ['pandas~=0.19.0'],
        'pandas:python_version=="2.7" or python_version>="3.5"': ['pandas'],
        'testing:python_version=="3.4"': ['pandas~=0.19.0'],
        'testing:python_version=="2.7" or python_version>="3.5"': ['pandas'],
        'testing': tests_requires,
    },
    zip_safe=True,
    entry_points={},
)

if __name__ == '__main__':
    setup(**setup_params)
