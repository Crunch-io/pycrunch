"""JSONObject and Element subclasses for Shoji objects.

See https://bitbucket.org/fumanchu/shoji/src/tip/spec.txt?at=default
for the latest Shoji specification.
"""

import json

import six

from pycrunch import elements
from pycrunch.lemonpy import URL


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
        super(Tuple, self).__init__(**members)

    def copy(self):
        """Return a (shallow) copy of self."""
        return self.__class__(self.session, self.entity_url, **self)

    def fetch(self, *args, **kwargs):
        r = self.session.get(self.entity_url, *args, **kwargs)
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
        new_members = {}
        for entity_url, tup in six.iteritems(members):
            url = entity_url
            if not isinstance(url, URL):
                url = URL(url, catalog_url.absolute)

            if tup is None:
                new_members[entity_url] = None
            else:
                new_members[entity_url] = Tuple(session, url, **tup)

        super(Index, self).__init__(**new_members)


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

    def create(self, entity=None, refresh=None):
        """POST the given Entity to this catalog to create a new resource.

        The 'entity' arg may be a complete shoji.Entity, in which case
        its .json will be POST'ed to this Catalog, or it may be a plain
        dict of attributes, in which case it will first be wrapped in an
        Entity. This latter case is more common simply for the fact that
        it results in cleaner calling code; compare:

            foo_catalog.create(pycrunch.shoji.Entity(my.session, bar=qux))

        versus:

            foo_catalog.create({"bar": qux})

        An entity is returned. If 'refresh' is:

            * True: an additional GET is performed and the Entity it fetches
              is returned (which is assumed to have the correct "self" member).
            * False: no additional GET is performed, and a minimal Entity
              is returned; either way, its "self" member is set to the URL
              of the newly-created resource.
            * None (the default): If an Entity was provided, behave like
              'refresh' was False. If not provided, behave like 'refresh'
              was True.
        """
        if refresh is None:
            refresh = (entity is None)

        if entity is None:
            entity = Entity(self.session)
        elif isinstance(entity, dict) and not isinstance(entity, Entity):
            entity = Entity(self.session, **entity)

        r = self.post(data=entity.json)
        new_url = r.headers["Location"]

        if refresh:
            entity = self.session.get(new_url).payload
        else:
            entity.self = new_url

        return entity

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
