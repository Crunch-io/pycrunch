"""LemonPy handlers for JSON payloads, especially those with an "element" member.

The base lemonpy parser for JSON returns the JSON text deserialized into
Python dicts, lists, etc. This module does the same, but wherever the base
parser would return a dict, it replaces that with a JSONObject instance.
JSONObject is itself a subclass of dict, so all the dict attributes and
methods are still present; however, the JSONObject has a .json property
and a nicer str output. It also allows reading keys as if they were
attributes, so instead of foo['bar'][0]['baz'] you can write foo.bar[0].baz.

When a JSON object has an "element" member, however, a specialized subclass
of JSONObject is chosen instead. These include a reference to the session,
and can therefore implement additional HTTP requests very naturally.
Any subclass of Element is automatically registered using its .element
class attribute. For example, the class definition:

    class Foo(Element):
        element = "myapp:foo"

...would result in any JSON object with an {"element": "myapp:foo"} member
being parsed into an instance of Foo, rather than a bare JSONObject.
"""

import json

import six

from requests.utils import get_environ_proxies

from pycrunch import lemonpy
from pycrunch.progress import DefaultProgressTracking
from .version import __version__

omitted = object()


class JSONObject(dict):
    """A base class for JSON objects."""

    @property
    def json(self):
        return json.dumps(self, indent=4)

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


class ElementMeta(type):
    """A metaclass for Element subclasses which registers them."""

    def __new__(cls, name, bases, d):
        new_type = type.__new__(cls, name, bases, d)
        if 'element' in d:
            # Skip any subclass which has no 'element' attribute,
            # (including Element itself!) to allow for additional
            # base classes.
            elements[d['element']] = new_type
        return new_type


@six.add_metaclass(ElementMeta)
class Element(JSONObject):
    """A base class for JSON objects classified by an 'element' member."""

    def __init__(__this__, session, **members):
        __this__.session = session
        members.setdefault("element", __this__.__class__.element)
        super(Element, __this__).__init__(**members)

    def copy(self):
        """Return a (shallow) copy of self."""
        return self.__class__(self.session, **self)


elements = {}


def parse_element(session, j):
    """Recursively replace dict with appropriate subclasses of JSONObjects."""
    t = type(j)
    if t is dict:
        for k, v in list(six.iteritems(j)):
            j[k] = parse_element(session, v)

        elem = j.get("element", None)
        if elem in elements:
            return elements[elem](session, **j)
        else:
            return JSONObject(**j)
    elif t is list:
        return [parse_element(session, i) for i in j]
    else:
        return j


class Document(Element):
    """A base class for complete Documents classified by 'element'.

    In addition to normal __getattr__ access to members, this class
    adds automatic GETs to collections nominated as URL's.

    Documents are considered "top-level" objects that may be returned
    as a complete payload; they therefore include helper functions
    for refreshing themselves (via HTTP GET), plus post, put, patch,
    and delete. Not every resource is guaranteed to respond to all.
    """

    navigation_collections = ()

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
                url = coll[key]
                return self.session.get(url).payload

        raise AttributeError(
            "%s has no attribute %s" % (self.__class__.__name__, key))

    def follow(self, key, qs=None):
        """GET the payload of the requested collection URL."""
        for collname in self.navigation_collections:
            coll = self.get(collname, {})
            if key in coll:
                url = coll[key]
                if qs is not None:
                    # Remove any existing qs, such as for URI Templates.
                    url = url.rsplit("?", 1)[0] + "?" + qs
                return self.session.get(url).payload

        raise AttributeError(
            "%s has no link %s" % (self.__class__.__name__, key))

    def refresh(self):
        """GET self.self, update self with its payload and return self."""
        r = self.session.get(self.self)
        if r.payload is None:
            raise TypeError("Response could not be parsed.", r)

        self.clear()
        self.update(r.payload)
        return self

    def post(self, data, *args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs["headers"].setdefault("Content-Type", "application/json")
        if not isinstance(data, six.string_types):
            data = json.dumps(data)
        return self.session.post(self.self, data, *args, **kwargs)

    def put(self, data, *args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs["headers"].setdefault("Content-Type", "application/json")
        if not isinstance(data, six.string_types):
            data = json.dumps(data)
        return self.session.put(self.self, data, *args, **kwargs)

    def patch(self, data, *args, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs["headers"].setdefault("Content-Type", "application/json")
        if not isinstance(data, six.string_types):
            data = json.dumps(data)
        return self.session.patch(self.self, data, *args, **kwargs)

    def delete(self):
        return self.session.delete(self.self)

# -------------------------- HTTP request helpers -------------------------- #


def parse_json_element_from_response(session, r):
    """Return the appropriate Element instance if possible, otherwise JSON."""
    if not r.text:
        return JSONObject()
    j = r.json()

    return parse_element(session, j)


class ElementResponseHandler(lemonpy.ResponseHandler):
    """A lemonpy response handler which parses to JSONObjects and Elements.

    In addition, this subclass traps 401 Unauthorized responses,
    then attempts to authenticate to Crunch.io, and then repeats
    the request. That should probably be moved out somewhere else.
    """

    parsers = {
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
        env_proxies = get_environ_proxies(r.request.url, no_proxy=None)
        r2 = self.session.send(r.request, proxies=env_proxies)

        # Add the previous requests to r.history so e.g. cookies get grabbed.
        r2.history.append(r)
        r2.history.append(login_r)

        return r2


class ElementSession(lemonpy.Session):

    headers = {
        "user-agent": "pycrunch/%s" % __version__
    }
    handler_class = ElementResponseHandler

    def __init__(self, email=None, password=None, token=None, domain=None,
                 progress_tracking=None):
        self.email = email
        self.password = password
        self.token = token
        self.domain = domain
        self.progress_tracking = progress_tracking or DefaultProgressTracking()
        super(ElementSession, self).__init__()
