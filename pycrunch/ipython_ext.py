"""IPython importable module."""

from pycrunch import pandaslib


def load_ipython_extension(ipython):
    # TODO: auto-inject the site in builtins drawn from an env var
    # token = ipython.config['InteractiveShellApp'].crunch_token
    # or
    # token = os.environ.get("CRUNCH_TOKEN", None)
    ipython.ns_table["builtin"]["dataframe_from_dataset"] = pandaslib.dataframe_from_dataset

    # TODO: do we want any magic?
    # ipython.register_magic_function(
    #     lambda line: pandaslib.dataframe_from_dataset(line.split(" ")),
    #     magic_kind='line', magic_name="crunch"
    # )
    pass


def unload_ipython_extension(ipython):
    # If you want your extension to be unloadable, put that logic here.
    pass
