import json
import lemonpy

omitted = object()


class JSONObject(dict):
    """A base class for JSON objects."""

    @property
    def json(self):
        return json.dumps(self, indent=4)

    def __repr__(self):
        return "%s.%s(**%s)" % (self.__module__, self.__class__.__name__,
                                # __repr__ is not indented!
                                json.dumps(self))

    def __str__(self):
        return "%s.%s(**%s)" % (self.__module__, self.__class__.__name__,
                                # __str__ is indented!
                                json.dumps(self, indent=4))

    def __getattr__(self, key):
        # Return the requested attribute if present in self.keys
        v = self.get(key, omitted)
        if v is not omitted:
            return v

        raise AttributeError(
            "%s has no attribute %s" % (self.__class__.__name__, key))

    def copy(self):
        """Return a (shallow) copy of self."""
        return self.__class__(**self)


class Element(JSONObject):
    """A base class for JSON objects classified by an 'element' member."""

    def __init__(_non_colliding_self, session, **members):
        _non_colliding_self.session = session
        members.setdefault("element", _non_colliding_self.__class__.element)
        super(Element, _non_colliding_self).__init__(**members)

    def __getattr__(self, key):
        # Return the requested attribute if present in self.keys
        v = self.get(key, omitted)
        if v is not omitted:
            return v

        # If the requested attribute is present in a URL collection,
        # do a GET and return its payload.
        for collname in self.navigation_collections:
            coll = self.get(collname, {})
            if key in coll:
                return self.session.get(coll[key]).payload

        raise AttributeError(
            "%s has no attribute %s" % (self.__class__.__name__, key))

    def copy(self):
        """Return a (shallow) copy of self."""
        return self.__class__(self.session, **self)

    def post(self, *args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs["headers"].setdefault("Content-Type", "application/json")
        return self.session.post(self.self, *args, **kwargs)

    def patch(self, *args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs["headers"].setdefault("Content-Type", "application/json")
        return self.session.patch(self.self, *args, **kwargs)


elements = {}


def parse_element(session, j):
    """Recursively replace dict with appropriate subclasses of JSONObjects."""
    if isinstance(j, dict):
        j = dict((k, parse_element(session, v)) for k, v in j.iteritems())

        elem = j.get("element", None)
        if elem in elements:
            return elements[elem](session, **j)
        else:
            return JSONObject(**j)
    elif isinstance(j, list):
        return [parse_element(session, i) for i in j]
    else:
        return j


# -------------------------- HTTP request helpers -------------------------- #


def parse_json_element_from_response(session, r):
    """Return the appropriate Element instance if possible, otherwise JSON."""
    if not r.text:
        return JSONObject()
    j = r.json()

    return parse_element(session, j)


class ElementResponseHandler(lemonpy.ResponseHandler):

    deserializers = {
        'application/json': parse_json_element_from_response
    }

    def status_401(self, r):
        login_url = r.json()["urls"]["login_url"]
        if r.request.url == login_url:
            raise ValueError("Log in was not successful.")

        creds = {'email': self.session.email, 'password': self.session.password}
        login_r = self.session.post(
            login_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(creds)
        )

        # Repeat the request now that we've logged in. What a hack.
        r.request.headers['Cookie'] = login_r.headers['Set-Cookie']
        r2 = self.session.send(r.request)

        # Add the previous requests to r.history so e.g. cookies get grabbed.
        r2.history.append(r)
        r2.history.append(login_r)

        return r2


class ElementSession(lemonpy.Session):

    headers = {}
    handler_class = ElementResponseHandler

    def __init__(self, email, password):
        super(ElementSession, self).__init__()
        self.email = email
        self.password = password
