#!/bin/bash -ex

SRCDIR=$WORKSPACE
VENVDIR=$WORKSPACE/venv
COVER_PACKAGE=pycrunch

virtualenv --clear $VENVDIR
$VENVDIR/bin/easy_install nose nosexcover coverage

#### 
echo .........compiling............
$VENVDIR/bin/python setup.py develop

echo .........TESTING............
$VENVDIR/bin/nosetests -s -v --with-xcoverage --with-xunit --cover-package=$COVER_PACKAGE --cover-erase "$@"
