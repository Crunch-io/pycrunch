import logging

import requests

requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)
urljoin = requests.compat.urljoin


class LemonPyError(Exception):
    """Base class for Exceptions which occur within LemonPy."""
    pass


class ClientError(LemonPyError):

    def __init__(self, response):
        super(ClientError, self).__init__(response, response.request.url,
                                          response.payload)

    @property
    def status_code(self):
        return self.args[0].status_code

    @property
    def message(self):
        return self.args[2]['message']


class ServerError(LemonPyError):

    def __init__(self, response):
        super(ServerError, self).__init__(response, response.request.url,
                                          response.payload)


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
        handler = getattr(self, "status_%dxx" % (code / 100), None)
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
        ct = r.headers.get("Content-Type").split(";", 1)[0]
        parser = self.parsers.get(ct, None)
        if parser is None:
            r.payload = None
        else:
            r.payload = parser(self.session, r)

    def status_2xx(self, r):
        self.parse_payload(r)
        return r

    # status_201 = status_2xx # The caller must look up r.headers["Location"]

    def status_204(self, r):
        # TODO: should we warn here if there is a payload?
        r.payload = None
        return r

    def status_4xx(self, r):
        self.parse_payload(r)
        raise ClientError(r)

    def status_5xx(self, r):
        self.parse_payload(r)
        raise ServerError(r)


class Session(requests.Session):

    headers = {}
    handler_class = ResponseHandler

    def __init__(self):
        super(Session, self).__init__()
        self.headers = self.__class__.headers
        self.hooks["response"] = self.handler_class(self)
