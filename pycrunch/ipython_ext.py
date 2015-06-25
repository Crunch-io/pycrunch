"""IPython importable module."""

import pycrunch


def load_ipython_extension(ipython):
    # The `ipython` argument is the currently active `InteractiveShell`
    # instance, which can be used in any way. This allows you to register
    # new magics or aliases, for example.
    pass


def unload_ipython_extension(ipython):
    # If you want your extension to be unloadable, put that logic here.
    pass


def connect(user, pw, site_url="https://us.crunch.io/api/"):
    session = pycrunch.Session(user, pw)
    site = session.get(site_url).payload
    return site
