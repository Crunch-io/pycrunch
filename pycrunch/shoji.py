"""JSONObject and Element subclasses for Shoji objects.

See https://bitbucket.org/fumanchu/shoji/src/tip/spec.txt?at=default
for the latest Shoji specification.
"""

import json

import time
from six.moves import urllib

import six

from pycrunch import elements
from pycrunch.lemonpy import URL, ClientError


class Tuple(elements.JSONObject):
    """A Shoji Tuple of attributes.

    Shoji Catalogs have an 'index' member, which maps URL's to Tuples.
    Shoji Entities have a 'body' member which is a Tuple.

    Like all JSONObjects, the items in a Tuple are readable as keys
    (e.g. tup['foo']) or as attributes (e.g. tup.foo). In addition,
    the URL of the Entity (whether from Catalog.index or Entity.self)
    is included as Tuple.entity_url. The Tuple.fetch method then assumes
    .entity_url as the URL to request, and either returns the complete
    Entity or raises TypeError if the response could not be parsed.
    """

    def __init__(self, session, entity_url, **members):
        self.session = session
        self.entity_url = entity_url
        self._entity = None
        elements.JSONObject.__init__(self, **members)

    def copy(self):
        """Return a (shallow) copy of self."""
        return self.__class__(self.session, self.entity_url, **self)

    def fetch(self, *args, **kwargs):
        r = self.session.get(self.entity_url.absolute, *args, **kwargs)
        if r.payload is None:
            raise TypeError("Response could not be parsed.", r)
        return r.payload

    @property
    def entity(self):
        """Fetch, cache, and return the shoji.Entity for self.entity_url.

        This is typically used from a Catalog Tuple to GET the associated
        Entity body attributes; e.g. foo_catalog['bar'].entity.body.qux.
        However, it can also be used from an Entity.body tuple to obtain
        a copy of the whole Entity; e.g. bar2 = bar.body.entity.
        """
        if self._entity is None:
            self._entity = self.fetch()
        return self._entity


class Index(elements.JSONObject):
    """The index of a Shoji Catalog.

    Shoji Catalogs have an 'index' member, which maps lemonpy.URL's to Tuples.
    """

    def __init__(self, session, catalog_url, **members):
        self.session = session
        self.catalog_url = catalog_url
        catalog_url_absolute, frag = urllib.parse.urldefrag(catalog_url.absolute)

        for entity_url, tup in six.iteritems(members):
            if tup is not None:
                url = entity_url
                if not hasattr(url, "relative_to"):  # Faster than isinstance(url, URL)
                    url = URL(url, catalog_url_absolute)

                members[entity_url] = Tuple(session, url, **tup)

        elements.JSONObject.__init__(self, **members)


class Catalog(elements.Document):
    """A Shoji Catalog."""

    element = "shoji:catalog"
    navigation_collections = ("catalogs", "orders", "views", "urls")

    def __init__(__this__, session, **members):
        if 'self' in members:
            if not isinstance(members['self'], URL):
                members['self'] = URL(members['self'], "")
            if 'index' in members:
                members['index'] = Index(session, members['self'], **members['index'])
        super(Catalog, __this__).__init__(session, **members)

    def create(self, entity=None):
        """POST the given Entity to this catalog to create a new resource.

        The 'entity' arg may be a complete shoji.Entity, in which case
        its .json will be POST'ed to this Catalog, or it may be a plain
        dict of attributes, in which case it will first be wrapped in an
        Entity. This latter case is more common simply for the fact that
        it results in cleaner calling code; compare:

            foo_catalog.create(pycrunch.shoji.Entity(my.session, bar=qux))

        versus:

            foo_catalog.create({"bar": qux})

        An entity is returned.
        """
        if entity is None:
            entity = Entity(self.session)
        elif isinstance(entity, dict) and not isinstance(entity, Entity):
            entity = Entity(self.session, **entity)
        return self._wait_for_progress(self.post(data=entity.json))

    def by(self, attr):
        """Return the Tuples of self.index indexed by the given 'attr' instead.

        If a given Tuple does not contain the specified attribute,
        it is not included. If more than one does, only one will be
        included (which one is undefined).

        The specified attr is not popped from the Tuple; it is merely
        copied to the output keys. Due to restrictions on Python dicts,
        specifying attrs which are not hashable will raise an error.
        """
        return elements.JSONObject(**dict(
            (tupl[attr], tupl)
            for tupl in six.itervalues(self.index)
            if attr in tupl
        ))

    def add(self, entity_url, attrs=None, **kwargs):
        """Add the given entity, plus any spurious index attributes (ICK), to self.

        This is a total hack because Crunch has an endpoint (dataset permissions)
        where non-tuples are included in a Catalog.index.
        """
        kwargs[entity_url] = attrs or {}
        p = json.dumps(dict(element="shoji:catalog", self=self.self, index=kwargs))
        return self.patch(data=p).payload

    def edit(self, entity_url, **attrs):
        """Update the catalog with the given entity attributes."""
        p = self.__class__(self.session, self=self.self, index={entity_url: attrs})
        return self.patch(data=p.json).payload

    def edit_index(self, index):
        """Update the catalog with the given (probably partial) index."""
        p = self.__class__(self.session, self=self.self, index=index)
        return self.patch(data=p.json).payload

    def drop(self, entity_url):
        """Delete the given entity from the catalog."""
        p = self.__class__(self.session, self=self.self, index={entity_url: None})
        return self.patch(data=p.json).payload

    def _wait_for_progress(self, r, timeout=30):
        if r.status_code == 201 and r.headers.get('Location') is not None:
            # Progress API convention, and it already completed.
            return self.session.get(r.headers['Location']).payload
        elif r.status_code == 202 and r.headers.get('Location') is not None:
            # Progress  API and it didn't complete.
            entity = Entity(self.session)
            entity.self = r.headers['Location']
            try:
                progress_url = r.payload['value']
            except:
                # Not a progress API return an incomplete entity, user will have to refresh it
                return entity
            else:
                return entity.wait_progress(progress_url, timeout=timeout)
        else:
            return r.payload


class Entity(elements.Document):

    element = "shoji:entity"
    navigation_collections = ("catalogs", "fragments", "views", "urls")

    def __init__(__this__, session, **members):
        members.setdefault("body", {})
        if 'self' in members:
            if not isinstance(members['self'], URL):
                members['self'] = URL(members['self'], "")
            members['body'] = Tuple(session, members['self'], **members['body'])
        super(Entity, __this__).__init__(session, **members)

    def edit(self, **body_attrs):
        """Update the entity with the new body attributes."""
        p = self.__class__(self.session, body=body_attrs)
        payload = super(Entity, self).patch(data=p.json).payload
        self.body.update(body_attrs)
        return payload

    def replace(self, entity=None):
        """PUT the given entity (default: self) to self.url."""
        if entity is None:
            entity = self
        return super(Entity, self).put(data=entity.json).payload

    def wait_progress(self, progress_url, timeout=None):
        begin = time.time()
        while timeout is None or time.time() - begin < timeout:
            r = self.session.get(progress_url)
            progress = r.payload['value']
            if progress['progress'] == -1:
                # Completed due to error
                raise CrunchError(progress['message'])
            elif progress['progress'] == 100:
                # Completed with success
                break
            time.sleep(0.5)
        else:
            # Loop completed due to timeout
            raise EntityProgressTimeoutError(self, progress_url)

        return self.refresh()


class View(elements.Document):

    element = "shoji:view"
    navigation_collections = ("views", "urls")

    def __init__(__this__, session, **members):
        if 'self' in members and not isinstance(members['self'], URL):
            members['self'] = URL(members['self'], "")
        super(View, __this__).__init__(session, **members)

    @property
    def value(self):
        return self['value']

    @value.setter
    def value(self, newvalue):
        """Update the View with the new value."""
        self['value'] = newvalue
        super(View, self).put(data=self.json)


class Order(elements.Document):

    element = "shoji:order"
    navigation_collections = ()

    def __init__(__this__, session, **members):
        if 'self' in members and not isinstance(members['self'], URL):
            members['self'] = URL(members['self'], "")
        super(Order, __this__).__init__(session, **members)

    @property
    def graph(self):
        return self['graph']

    @graph.setter
    def graph(self, newgraph):
        """Update the Order with the new graph."""
        self['graph'] = newgraph
        super(Order, self).put(data=self.json)


class EntityProgressTimeoutError(Exception):
    def __init__(self, entity, progress_url):
        super(EntityProgressTimeoutError, self).__init__(
            'Entity Progress did not complete before timeout. '
            'Trap this exception and call exc.entity.wait_progress(exc.progress_url) '
            'to wait for completion explicitly.'
        )
        self.entity = entity
        self.progress_url = progress_url


class CrunchError(ClientError):
    # For backward compatibility inherit from ClientError

    def __init__(self, message):
        Exception.__init__(self, message)

    @property
    def status_code(self):
        return None

    @property
    def message(self):
        return self.args[0]