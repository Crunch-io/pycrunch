pycrunch
========

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
    >>> site = pycrunch.connect(api_key="DFIJFIJWIEJIJFKSJLKKDJKFJSLLSLSL", site_url="https://your-domain.crunch.io/api/")

Or, if you don't have an API Key:

    >>> site = pycrunch.connect("me@mycompany.com", "yourpassword", "https://your-domain.crunch.io/api/")

Then, you can create an API Key:

    >>> apk = site.apikeys.create({"body": {"name": "API Key"}})
    >>> apk.refresh()
    >>> site_via_api_key = pycrunch.connect(api_key=apk.body["key"], site_url="https://your-domain.crunch.io/api/")

Or, if you have a crunch access token:

    >>> import pycrunch
    >>> site = pycrunch.connect_with_token("DFIJFIJWIEJIJFKSJLKKDJKFJSLLSLSL", "https://your-domain.crunch.io/api/")

Then, you can browse the site. Use `print` to pretty-indent JSON payloads:

    >>> print(site)
    pycrunch.shoji.Catalog(**{
        "element": "shoji:catalog",
        "self": "https://your-domain.crunch.io/api/",
        "description": "The API root.",
        "catalogs": {
            "datasets": "https://your-domain.crunch.io/api/datasets/",
            ...
        },
        "urls": {
            "logout_url": "https://your-domain.crunch.io/api/logout/",
            ...
        },
        "views": {
            "migration": "https://your-domain.crunch.io/api/migration/"
        }
    })

URI's in payloads' catalogs, views, fragments, and urls collections
are followable automatically:

    >>> print(site.datasets)
    pycrunch.shoji.Catalog(**{
        "self": "https://your-domain.crunch.io/api/datasets/",
        "element": "shoji:catalog",
        "index": {
            "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/": {
                "owner_display_name": "me@mycompany.com",
                "description": "",
                "id": "dbf9fca7b727",
                "owner_id": "https://your-domain.crunch.io/api/users/253b68/",
                "archived": false,
                "name": "Hog futures tracking (May 2014)"
            },
        },
        ...
    })

Each recognized JSON payload also automatically gives dotted-attribute
access to the members of each JSON object:

    >>> print(site.datasets.index.values()[0])
    pycrunch.shoji.Tuple(**{
        "owner_display_name": "me@mycompany.com",
        "description": "",
        "id": "dbf9fca7b727",
        "owner_id": "https://your-domain.crunch.io/api/users/253b68/",
        "archived": false,
        "name": "Hog futures tracking (May 2014)"
    })

Responses may also possess additional helpers, like the `entity` property of
each Tuple in a catalog's index, which follows the link to the Entity resource:

    >>> print(site.datasets.index.values()[0].entity_url)
    "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/"

    >>> print(site.datasets.index.values()[0].entity)
    pycrunch.shoji.Entity(**{
        "self": "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/",
        "element": "shoji:entity",
        "description": "Detail for a given dataset",
        "body": {
            "archived": false,
            "user_id": "253b68",
            "name": "Hog futures tracking (May 2014)"
            "weight": "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/variables/36f5404/",
            "creation_time": "2014-03-06T18:23:26.780752+00:00",
            "description": ""
        },
        "catalogs": {
            "batches": "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/batches/",
            "joins": "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/joins/",
            "variables": "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/variables/",
            "filters": "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/filters/",
            ...
        },
        "views": {
            "cube": "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/cube/",
            ...
        },
        "urls": {
            "revision_url": "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/revision/",
            ...
        },
        "fragments": {
            "table": "https://your-domain.crunch.io/api/datasets/dbf9fca7b727/table/"
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
    >>> print(ds.table.data)
    pycrunch.elements.JSONObject(**{
        "e7f361628": [
            1,
            2,
            {"?": -1},
            2
        ]
    })

To access a Pandas Dataframe of the data in your dataset:

    >>> from pycrunch import pandaslib as crunchpandas
    >>> df = crunchpandas.dataframe_from_dataset(site,'baadf00d000339d9faadg00beab11e')
    >>> print(df)
    < Draws a dataframe table >
