from __future__ import division

import logging

import six
from six.moves import urllib
from six.moves.http_cookiejar import Cookie

import requests

requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)
urljoin = requests.compat.urljoin


class LemonPyError(Exception):
    """Base class for Exceptions which occur within LemonPy."""
    pass


class ClientError(LemonPyError):

    def __init__(self, response):
        args = []
        if not isinstance(response, six.string_types):
            args = [response.request.url, response.payload]

        super(ClientError, self).__init__(response, *args)

    @property
    def status_code(self):
        return self.args[0].status_code

    @property
    def message(self):
        return self.args[2]['message']


class ServerError(LemonPyError):

    def __init__(self, response):
        args = []
        if not isinstance(response, six.string_types):
            args = [response.request.url, response.payload]
        super(ServerError, self).__init__(response, *args)


class ResponseHandler(object):
    """A requests.Session response-hook aware of status and Content-Type.

    When an instance of this class is set as Session.hooks['response'],
    all Response objects are passed to its __call__ method. That method
    looks for a handler on itself for the specific response status code,
    such as "self.status_204(r)", passes the Response object to it,
    and returns its output (which MUST be a Response object, and is
    typically the given one). If no specific handler method is found,
    a more general handler is sought for the class of the response status,
    such as "self.status_2xx(r)". If neither is found, an AttributeError
    is raised.

    Assuming a handler is found, it should call self.parse_payload(r),
    which attempts to parse the Response based on its Content-Type.
    """

    parsers = {
        'application/json': lambda session, r: r.json()
    }

    def __init__(self, session):
        self.session = session

    def __call__(self, r, *args, **kwargs):
        code = r.status_code

        # First, try the specific response status code
        handler = getattr(self, "status_%d" % code, None)
        if handler is not None:
            return handler(r)

        # If that fails, look for a Nxx code
        handler = getattr(self, "status_%dxx" % (code // 100), None)
        if handler is not None:
            return handler(r)

        raise AttributeError("No handler found for response status %s" %
                             r.status_code)

    def parse_payload(self, r):
        """Attach a .payload to the given Response.

        If the Content-Type of the given Response has a parser function
        registered in self.parsers, it will be called as parser(session, r);
        whatever it returns will be attached as r.payload. If no parser
        function exists, r.payload is set to None, and the caller will
        have to examine the Response directly to determine its payload.
        """
        ct = r.headers.get("Content-Type", "").split(";", 1)[0]
        parser = self.parsers.get(ct)
        r.payload = parser(self.session, r) if parser else None

    def status_2xx(self, r):
        self.parse_payload(r)
        return r

    # status_201 = status_2xx # The caller must look up r.headers["Location"]

    def status_204(self, r):
        # TODO: should we warn here if there is a payload?
        r.payload = None
        return r

    def status_301(self, r):
        # Support permanent redirects
        return r

    def status_302(self, r):
        # Support redirects
        return r

    def status_303(self, r):
        self.parse_payload(r)
        return r

    def status_4xx(self, r):
        self.parse_payload(r)
        raise ClientError(r)

    def status_5xx(self, r):
        self.parse_payload(r)
        raise ServerError(r)


def make_cookie(name, value, domain):
    '''
        Makes a cookie with provided name and value.
    '''
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=None,
        discard=False,
        comment=None,
        comment_url=None,
        rest=None
    )


class Session(requests.Session):

    headers = {
        "Accept-Encoding": "gzip",
    }
    handler_class = ResponseHandler

    def __init__(self):
        super(Session, self).__init__()

        self.headers.update(self.__class__.headers)
        self.proxies = urllib.request.getproxies()

        if self.token:
            domain = self.domain or 'local.crunch.io'
            self.cookies.set_cookie(make_cookie('token', self.token, domain))

        self.hooks["response"] = self.handler_class(self)


class URL(str):
    """A subclass of str for URL's. self.absolute = urljoin(self.base, self)."""

    def __new__(cls, value, *args, **kwargs):
        return str.__new__(cls, value)

    def __init__(self, value, base):
        self.base = base

    @property
    def absolute(self):
        """Return self, which may be relative to self.base, as an absolute URL."""
        return urljoin(self.base, self)

    def relative_to(self, base):
        """Return self, relative to the given absolute base."""
        base = urllib.parse.urlparse(base)
        new = urllib.parse.urlparse(self.absolute)

        if base.scheme != new.scheme or base.netloc != new.netloc:
            return self.absolute

        base_path = base.path.split('/')[:-1]
        new_path = new.path.split('/')
        while base_path and new_path:
            a, b = base_path[0], new_path[0]
            if a != b:
                break
            base_path.pop(0)
            new_path.pop(0)
        new_path = (['..'] * len(base_path)) + new_path
        new_path = '/'.join(new_path)

        return urllib.parse.urlunparse(
            ("", "", new_path, new.params, new.query, new.fragment)
        )
