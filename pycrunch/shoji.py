from pycrunch import elements


class Catalog(elements.Element):

    element = "shoji:catalog"
    navigation_collections = ("catalogs", "views", "urls")

    def create(self, entity=None, refresh=None):
        """POST the given Entity to this catalog to create a new resource.

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

        r = self.post(data=entity.json)
        new_url = r.headers["Location"]

        if refresh:
            entity = self.session.get(new_url).payload
        else:
            entity.self = new_url

        return entity

    def by(self, attr, index_attr='url'):
        """Return the tuples of self.index indexed by the given 'attr' instead.

        If a given tuple does not contain the specified attribute,
        it is not included. If more than one does, only one will be
        included (which one is undefined).

        The specified attr is not popped from the tuples; it is merely
        copied to the output keys. Due to restrictions on Python dicts,
        specifying attrs which are not hashable will raise an error.

        By default, the keys of self.index (which are always URL's) are
        included in the returned tuples as an additional "url" member.
        If this name collides with an attribute that already exists
        in the tuples, specify a different 'index_attr' to use.
        """
        out = elements.JSONObject()
        for url, tupl in self.index.iteritems():
            if attr in tupl:
                k = tupl[attr]
                out[k] = v = tupl.copy()
                v[index_attr] = url

        return out


class Entity(elements.Element):

    element = "shoji:entity"
    navigation_collections = ("catalogs", "fragments", "views", "urls")

    def __init__(me, session, **members):
        members.setdefault("body", {})
        super(Entity, me).__init__(session, **members)


class View(elements.Element):

    element = "shoji:view"
    navigation_collections = ("views", "urls")


elements.elements.update({
    "shoji:catalog": Catalog,
    "shoji:entity": Entity,
    "shoji:view": View,
})
