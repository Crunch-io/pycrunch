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
import warnings

from requests.utils import get_environ_proxies

from pycrunch import lemonpy
from pycrunch.progress import DefaultProgressTracking
from .version import __version__

try:
    # Python 2
    from urllib import urlencode, quote
    from urlparse import urlparse
except ImportError:
    # Python 3
    from urllib.parse import urlencode, quote, urlparse

omitted = object()


class JSONObject(dict):
    """A base class for JSON objects."""

    @property
    def json(self):
        return json.dumps(self, indent=None, separators=(",", ":"))

    @property
    def pretty(self):
        return json.dumps(self, indent=4)

    def __str__(self):
        return "%s.%s(**%s)" % (
            self.__module__,
            self.__class__.__name__,
            # __str__ is indented!
            json.dumps(self, indent=4),
        )

    def __getattr__(self, key):
        # Return the requested attribute if present in self.keys
        v = self.get(key, omitted)
        if v is not omitted:
            return v

        raise AttributeError("%s has no attribute %s" % (self.__class__.__name__, key))

    def copy(self):
        """Return a (shallow) copy of self."""
        return self.__class__(**self)


class ElementMeta(type):
    """A metaclass for Element subclasses which registers them."""

    def __new__(cls, name, bases, d):
        new_type = type.__new__(cls, name, bases, d)
        if "element" in d:
            # Skip any subclass which has no 'element' attribute,
            # (including Element itself!) to allow for additional
            # base classes.
            elements[d["element"]] = new_type
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

    navigation_collections = {}

    def __getattr__(self, key):
        # Return the requested attribute if present in self.keys
        v = self.get(key, omitted)
        if v is not omitted:
            return v

        headers = {"Accept": "application/json"}
        # If the requested attribute is present in a URL collection,
        # do a GET and return its payload.
        for collname in self.navigation_collections:
            coll = self.get(collname, {})
            if key in coll:
                url = coll[key]
                return self.session.get(url, headers=headers).payload

        raise AttributeError("%s has no attribute %s" % (self.__class__.__name__, key))

    def void(self, key, **members):
        """Return a dummy Document without populating it via HTTP GET.

        For example, call `root.void("foo").post(entity)` to POST an entity to
        the "foo" resource without having to first GET the "foo" resource. This
        can be a useful optimization for large resources that are expensive to GET.

        This returns a Document instance with a `self` attribute, but no
        additional members other than those provided. It can't, because
        populating those would require a GET, which this method purposefully
        avoids. If you later need to populate the Document, simply call its
        refresh() method to perform the GET.

        The returned Document will have `post`, `put`, `patch`, and `delete`
        methods, which only need the `self` URL to function properly. If a
        different Document subclass can be determined from the navigation
        collection in which the key is found, it will be used and some of
        its methods may also work properly if they only need the `self` URL.
        If they need additional members, you must either provide them as keyword
        arguments to this method, or call .refresh().

        Use this method sparingly, because it hard-codes assumptions about
        the response which would have been returned if an HTTP GET had been
        performed. Inspecting the actual response allows the API to evolve
        more easily over time, allowing redirects and other response codes,
        additional response headers, improved media types, and new hyperlinks,
        without having to rewrite clients. When fetching the actual response
        becomes too expensive, this method can be used to trade evolvability
        for speed; where possible, you should also discuss with the service
        provider whether the GET can be made less expensive to have both.
        """
        for collname, cls in six.iteritems(self.navigation_collections):
            coll = self.get(collname, {})
            if key in coll:
                return cls(self.session, self=coll[key], **members)

        raise AttributeError("%s has no attribute %s" % (self.__class__.__name__, key))

    def follow(self, key, qs=None, **kwargs):
        """GET the payload of the requested collection URL."""
        url = None
        for collname in self.navigation_collections:
            coll = self.get(collname, {})
            if key in coll:
                url = coll[key]
                break

        if url is None:
            raise AttributeError("%s has no link %s" % (self.__class__.__name__, key))

        if isinstance(qs, dict):
            template_lookups = {"{%s}" % k: k for k in qs.keys()}
            pruned_qs = {}
            for tpl, v in template_lookups.items():
                if tpl in url:
                    url = url.replace(tpl, quote(qs[v], safe=""))
                else:
                    pruned_qs[v] = qs[v]
            qs = urlencode(pruned_qs)

        if qs is not None:
            # Remove any existing qs, such as for URI Templates.
            url = url.rsplit("?", 1)[0] + "?" + qs
        kwargs.setdefault("headers", {})
        kwargs["headers"].setdefault("Accept", "application/json, */*")
        return self.session.get(url, **kwargs).payload

    def refresh(self):
        """GET self.self, update self with its payload and return self."""
        r = self.session.get(self.self)
        if r.payload is None:
            raise TypeError("Response could not be parsed.", r)

        self.clear()
        self.update(r.payload)
        return self

    def post(self, data, *args, **kwargs):
        kwargs.setdefault("headers", {})
        kwargs["headers"].setdefault("Content-Type", "application/json")
        if not isinstance(data, six.string_types):
            data = json.dumps(data)
        return self.session.post(self.self, data, *args, **kwargs)

    def put(self, data, *args, **kwargs):
        kwargs.setdefault("headers", {})
        kwargs["headers"].setdefault("Content-Type", "application/json")
        if not isinstance(data, six.string_types):
            data = json.dumps(data)
        return self.session.put(self.self, data, *args, **kwargs)

    def patch(self, data, *args, **kwargs):
        kwargs.setdefault("headers", {})
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

    parsers = {"application/json": parse_json_element_from_response}

    def status_401(self, r):
        login_url = r.json()["urls"]["login_url"]
        if r.request.url == login_url:
            # This means that the requests was made on the login_url, so it was
            # an authentication attempt. It means the login failed.
            raise ValueError("Log in was not successful.")

        if self.session.token:
            # Do not re-attempt login if this is an API key session.
            return r

        creds = {"email": self.session.email, "password": self.session.password}
        login_r = self.session.post(
            login_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(creds),
        )

        # Repeat the request now that we've logged in. What a hack.
        r.request.headers["Cookie"] = login_r.headers["Set-Cookie"]
        env_proxies = get_environ_proxies(r.request.url, no_proxy=None)
        r2 = self.session.send(r.request, proxies=env_proxies)

        # Add the previous requests to r.history so e.g. cookies get grabbed.
        r2.history.append(r)
        r2.history.append(login_r)

        return r2


class ElementSession(lemonpy.Session):

    headers = {"user-agent": "pycrunch/%s" % __version__}
    handler_class = ElementResponseHandler

    def __init__(
        self, email=None, password=None, token=None, site_url=None, progress_tracking=None
    ):
        if not site_url and token:
            raise ValueError("Must include a `site_url` host to connect to")
        self.__email = email
        self.__password = password
        self.token = token
        self.site_url = site_url
        self.domain = urlparse(site_url).netloc if site_url else None
        self.progress_tracking = progress_tracking or DefaultProgressTracking()
        super(ElementSession, self).__init__()

    @property
    def root(self):
        if not self.site_url:
            raise ValueError("Session must be initialized with `site_url`")
        return self.get(self.site_url).payload

    @property
    def email(self):
        warnings.warn(
            "`session.email` is being deprecated. Read from `conn.user.body.email`.",
            PendingDeprecationWarning,
        )
        if self.__email is None:
            self.__email = self.root.user["body"]["email"]
        return self.__email

    @property
    def password(self):
        warnings.warn(
            "`session.password` is being deprecated.", PendingDeprecationWarning
        )
        return self.__password
