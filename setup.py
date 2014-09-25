#!/usr/bin/env python
# coding: utf-8

import os
thisdir = os.path.abspath(os.path.dirname(__file__))

from setuptools import setup, find_packages

version = open(os.path.join(thisdir, 'version.txt'), 'rb').read().strip()


def get_long_desc():
    root_dir = os.path.dirname(__file__)
    if not root_dir:
        root_dir = '.'
    return open(os.path.join(root_dir, 'README.md')).read()


setup(
    name='pycrunch',
    version=version,
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
    license='Proprietary',
    install_requires=[
        'requests>=2.3.0',
    ],
    tests_require=[
        'nose>=1.1.2',
    ],
    packages=find_packages(),
    namespace_packages=[],
    include_package_data=True,
    package_data={
        'pycrunch': ['*.json', '*.csv']
    },
    zip_safe=True,
    entry_points={},
)
