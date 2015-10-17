import io
import os

thisdir = os.path.abspath(os.path.dirname(__file__))
version_fn = os.path.join(thisdir, '..', 'version.txt')
with io.open(version_fn, encoding='utf-8') as f:
    version = f.read().strip()