"""PyCrunch

A Python client library for Crunch.io.


Using pycrunch
--------------

To use pycrunch in your project, run:

    $ python setup.py develop

This will make the code in this directory available to other projects.

Getting started
---------------

Start a simple site session via:

    >>> import pycrunch
    >>> site = pycrunch.connect("me@mycompany.com", "yourpassword", "https://beta.crunch.io/api/")

Or, if you have a crunch access token:

    >>> import pycrunch
    >>> site = pycrunch.connect_with_token("DFIJFIJWIEJIJFKSJLKKDJKFJSLLSLSL", "https://beta.crunch.io/api/")


Then, you can browse the site. Use `print` to pretty-indent JSON payloads:

    >>> print site
    pycrunch.shoji.Catalog(**{
        "element": "shoji:catalog",
        "self": "https://beta.crunch.io/api/",
        "description": "The API root.",
        "catalogs": {
            "datasets": "https://beta.crunch.io/api/datasets/",
            "specifications": "https://beta.crunch.io/api/specifications/",
            ...
        },
        "urls": {
            "logout_url": "https://beta.crunch.io/api/logout/",
            ...
        },
        "views": {
            "migration": "https://beta.crunch.io/api/migration/"
        }
    })

URI's in payloads' catalogs, views, fragments, and urls collections
are followable automatically:

    >>> print site.datasets
    pycrunch.shoji.Catalog(**{
        "self": "https://beta.crunch.io/api/datasets/",
        "element": "shoji:catalog",
        "index": {
            "https://beta.crunch.io/api/datasets/dbf9fca7b727/": {
                "owner_display_name": "me@mycompany.com",
                "description": "",
                "id": "dbf9fca7b727",
                "owner_id": "https://beta.crunch.io/api/users/253b68/",
                "archived": false,
                "name": "Hog futures tracking (May 2014)"
            },
        },
        ...
    })

Each recognized JSON payload also automatically gives dotted-attribute
access to the members of each JSON object:

    >>> print site.datasets.index.values()[0]
    pycrunch.shoji.Tuple(**{
        "owner_display_name": "me@mycompany.com",
        "description": "",
        "id": "dbf9fca7b727",
        "owner_id": "https://beta.crunch.io/api/users/253b68/",
        "archived": false,
        "name": "Hog futures tracking (May 2014)"
    })

Responses may also possess additional helpers, like the `entity` property of
each Tuple in a catalog's index, which follows the link to the Entity resource:

    >>> print site.datasets.index.values()[0].entity_url
    "https://beta.crunch.io/api/datasets/dbf9fca7b727/"

    >>> print site.datasets.index.values()[0].entity
    pycrunch.shoji.Entity(**{
        "self": "https://beta.crunch.io/api/datasets/dbf9fca7b727/",
        "element": "shoji:entity",
        "description": "Detail for a given dataset",
        "specification": "https://beta.crunch.io/api/specifications/datasets/",
        "body": {
            "archived": false,
            "user_id": "253b68",
            "name": "Hog futures tracking (May 2014)"
            "weight": "https://beta.crunch.io/api/datasets/dbf9fca7b727/variables/36f5404/",
            "creation_time": "2014-03-06T18:23:26.780752+00:00",
            "description": ""
        },
        "catalogs": {
            "batches": "https://beta.crunch.io/api/datasets/dbf9fca7b727/batches/",
            "joins": "https://beta.crunch.io/api/datasets/dbf9fca7b727/joins/",
            "variables": "https://beta.crunch.io/api/datasets/dbf9fca7b727/variables/",
            "filters": "https://beta.crunch.io/api/datasets/dbf9fca7b727/filters/",
            ...
        },
        "views": {
            "cube": "https://beta.crunch.io/api/datasets/dbf9fca7b727/cube/",
            ...
        },
        "urls": {
            "revision_url": "https://beta.crunch.io/api/datasets/dbf9fca7b727/revision/",
            ...
        },
        "fragments": {
            "table": "https://beta.crunch.io/api/datasets/dbf9fca7b727/table/"
        }
    })

You typically add new resources to a Catalog via its `create` method:

    >>> ds = site.datasets.create({"body": {
            'name': "My first dataset"
        }}, refresh=True)
    >>> gender = ds.variables.create({"body": {
            'name': 'Gender',
            'alias': 'gender',
            'type': 'categorical',
            'categories': [
                {'id': -1, 'name': 'No Data', 'numeric_value': None, 'missing': True},
                {'id': 1, 'name': 'M', 'numeric_value': None, 'missing': False},
                {'id': 2, 'name': 'F', 'numeric_value': None, 'missing': False}
            ],
            'values': [1, 2, {"?": -1}, 2]
        }}, refresh=True)
    >>> print ds.table.data
    pycrunch.elements.JSONObject(**{
        "e7f361628": [
            1,
            2,
            {"?": -1},
            2
        ]
    })
"""

from six.moves import urllib

from pycrunch import cubes
from pycrunch import elements
from pycrunch import shoji
from pycrunch import importing
from pycrunch.lemonpy import ClientError, ServerError, urljoin
from pycrunch.version import __version__

Session = elements.ElementSession

__all__ = [
    'cubes',
    'elements',
    'shoji',
    'importing',
    'ClientError', 'ServerError', 'CrunchError'
    'Session',
    'urljoin',
    'connect', 'connect_with_token'
]


class CrunchError(elements.Element):

    element = "crunch:error"


class CrunchTable(elements.Document):

    element = "crunch:table"

session = None

def connect(user, pw, site_url="https://us.crunch.io/api/"):
    """
    Log in to Crunch with a user/pw; return the top-level Site payload.  Using
    this or the other connect method (the first time only) stores a reference
    to the session created in pycrunch.session for future use.

    Returns the API Root Entity, or errors if unable to connect.
    """
    global session
    ret = Session(user, pw).get(site_url).payload
    if session is None:
        session = ret
    return ret


def connect_with_token(token, site_url="https://us.crunch.io/api/"):
    """
    Log in to Crunch with a token; return the top-level Site payload. Using
    this or the other connect method (the first time only) stores a reference
    to the session created in pycrunch.session for future use.

    Returns the API Root Entity, or errors if unable to connect.
    """
    global session
    ret = Session(
        token=token,
        domain=urllib.parse.urlparse(site_url).netloc
    ).get(site_url).payload
    if session is None:
        session = ret
    return ret

def get_dataset(dataset_name_or_id, site=None):
    """
    Retrieve a reference to a given dataset (either by name, or ID) if it exists.
    This method uses the library singleton session if the optional "site"
    parameter is not provided.
    
    Returns a Dataset Entity record if the dataset exsists.
    Raises a KeyError if no such dataset exists.
    """
    global session
    if site is None:
        site = session

    ds_catalog = site.datasets
    try:
        dataset = ds_catalog.by('name')[dataset_name_or_id].entity
    except KeyError:
        dataset = ds_catalog.by('id')[dataset_name_or_id].entity
    return dataset

