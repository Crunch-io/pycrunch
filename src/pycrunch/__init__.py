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

    >> import pycrunch
    >> site = pycrunch.connect("me@mycompany.com", "yourpassword", "https://app.crunch.io/api/")

Or, if you have a crunch access token:

    >> import pycrunch
    >> site = pycrunch.connect_with_token("DFIJFIJWIEJIJFKSJLKKDJKFJSLLSLSL", "https://app.crunch.io/api/")


Then, you can browse the site. Use `print` to pretty-indent JSON payloads:

    >> print site
    pycrunch.shoji.Catalog(**{
        "element": "shoji:catalog",
        "self": "https://app.crunch.io/api/",
        "description": "The API root.",
        "catalogs": {
            "datasets": "https://app.crunch.io/api/datasets/",
            ...
        },
        "urls": {
            "logout_url": "https://app.crunch.io/api/logout/",
            ...
        },
        "views": {
            "migration": "https://app.crunch.io/api/migration/"
        }
    })

URI's in payloads' catalogs, views, fragments, and urls collections
are followable automatically:

    >> print site.datasets
    pycrunch.shoji.Catalog(**{
        "self": "https://app.crunch.io/api/datasets/",
        "element": "shoji:catalog",
        "index": {
            "https://app.crunch.io/api/datasets/dbf9fca7b727/": {
                "owner_display_name": "me@mycompany.com",
                "description": "",
                "id": "dbf9fca7b727",
                "owner_id": "https://app.crunch.io/api/users/253b68/",
                "archived": false,
                "name": "Hog futures tracking (May 2014)"
            },
        },
        ...
    })

Each recognized JSON payload also automatically gives dotted-attribute
access to the members of each JSON object:

    >> print site.datasets.index.values()[0]
    pycrunch.shoji.Tuple(**{
        "size": {
            "rows": 6,
            "columns": 8
        },
        "archived": false,
        "owner_name": "Me",
        "description": "",
        "end_date": null,
        "owner_id": "https://app.crunch.io/api/users/a69402/",
        "current_editor": "https://app.crunch.io/api/users/a69402/",
        "creation_time": "2016-03-02T22:19:14.463000+00:00",
        "current_editor_name": "The Editor",
        "start_date": null,
        "permissions": {
            "edit": true,
            "change_permissions": true,
            "add_users": true,
            "change_weight": true,
            "view": true
        },
        "id": "1234",
        "name": "Some Kind of Love"
    })


Responses may also possess additional helpers, like the `entity` property of
each Tuple in a catalog's index, which follows the link to the Entity resource:

    >> print site.datasets.index.values()[0].entity_url
    "https://app.crunch.io/api/datasets/1234/"

    >> print site.datasets.index.values()[0].entity
    pycrunch.shoji.Entity(**{u'body': {u'archived': False,
           u'creation_time': u'2015-03-18T01:56:12.462000',
           u'current_editor': u'https://app.crunch.io/api/users/00002/',
           u'current_editor_name': u'Jean-Luc Picard',
           u'description': u'',
           u'end_date': None,
           u'id': u'1234',
           u'name': u'a_econ_few_columns',
           u'notes': u'',
           u'owner': u'https://app.crunch.io/api/users/00002/',
           u'permissions': {u'add_users': True,
                            u'change_permissions': True,
                            u'change_weight': True,
                            u'edit': True,
                            u'view': True},
           u'size': {u'columns': 14, u'rows': 1000},
           u'start_date': None,
           u'weight': u'https://app.crunch.io/api/datasets/1234/variables/c1820eb7befd4704beacfdbcb430969c/'},
           u'catalogs': {u'actions': u'https://app.crunch.io/api/datasets/1234/actions/',
                         u'batches': u'https://app.crunch.io/api/datasets/1234/batches/',
                         u'comparisons': u'https://app.crunch.io/api/datasets/1234/comparisons/',
                         u'decks': u'https://app.crunch.io/api/datasets/1234/decks/',
                         u'filters': u'https://app.crunch.io/api/datasets/1234/filters/',
                         u'forks': u'https://app.crunch.io/api/datasets/1234/forks/',
                         u'joins': u'https://app.crunch.io/api/datasets/1234/joins/',
                         u'multitables': u'https://app.crunch.io/api/datasets/1234/multitables/',
                         u'permissions': u'https://app.crunch.io/api/datasets/1234/permissions/',
                         u'savepoints': u'https://app.crunch.io/api/datasets/1234/savepoints/',
                         u'variables': u'https://app.crunch.io/api/datasets/1234/variables/',
                         u'weight_variables': u'https://app.crunch.io/api/datasets/1234/weight_variables/'},
           u'description': u'Detail for a given dataset',
           u'element': u'shoji:entity',
           u'fragments': {u'exclusion': u'https://app.crunch.io/api/datasets/1234/exclusion/',
                          u'main_deck': u'https://app.crunch.io/api/datasets/1234/decks/bf57e39d42ae472b91e03de9a299e7c4/',
                          u'state': u'https://app.crunch.io/api/datasets/1234/state/',
                          u'stream': u'https://app.crunch.io/api/datasets/1234/stream/',
                          u'table': u'https://app.crunch.io/api/datasets/1234/table/'},
           u'self': u'https://app.crunch.io/api/datasets/1234/',
           u'urls': {u'editor_url': u'https://app.crunch.io/api/users/00002/',
                     u'owner_url': u'https://app.crunch.io/api/users/00002/',
                     u'user_url': u'https://app.crunch.io/api/users/00002/'},
           u'views': {u'applied_filters': u'https://app.crunch.io/api/datasets/1234/filters/applied/',
                      u'cube': u'https://app.crunch.io/api/datasets/1234/cube/',
                      u'export': u'https://app.crunch.io/api/datasets/1234/export/',
                      u'summary': u'https://app.crunch.io/api/datasets/1234/summary/'}}
            )

You typically add new resources to a Catalog via its `create` method:

    >> ds = site.datasets.create({"body": {
            'name': "My first dataset"
        }}, refresh=True)
    >> gender = ds.variables.create({"body": {
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
    >> print ds.table.data
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
from pycrunch.shoji import TaskError, TaskProgressTimeoutError
from pycrunch import importing
from pycrunch.lemonpy import ClientError, ServerError, urljoin
from pycrunch.version import __version__

Session = elements.ElementSession

__all__ = [
    'cubes',
    'elements',
    'shoji',
    'TaskError', 'TaskProgressTimeoutError',
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


def connect(user, pw, site_url="https://app.crunch.io/api/",
            progress_tracking=None, session_class=Session):
    """
    Log in to Crunch with a user/pw; return the top-level Site payload.  Using
    this or the other connect method (the first time only) stores a reference
    to the session created in pycrunch.session for future use.

    Returns the API Root Entity, or errors if unable to connect.
    """
    global session
    ret = session_class(
        user, pw, progress_tracking=progress_tracking
    ).get(site_url).payload
    if session is None:
        session = ret
    return ret


def connect_with_token(token, site_url="https://us.crunch.io/api/",
                       progress_tracking=None, session_class=Session):
    """
    Log in to Crunch with a token; return the top-level Site payload. Using
    this or the other connect method (the first time only) stores a reference
    to the session created in pycrunch.session for future use.

    Returns the API Root Entity, or errors if unable to connect.
    """
    global session
    ret = session_class(
        token=token,
        domain=urllib.parse.urlparse(site_url).netloc,
        progress_tracking=progress_tracking
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
