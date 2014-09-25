import requests
from requests.compat import urljoin


class LemonPyError(Exception):
    """Base class for Exceptions which occur within LemonPy."""
    pass


class ClientError(LemonPyError):

    def __init__(self, response):
        super(ClientError, self).__init__(response, response.request.url, response.payload)


class ServerError(LemonPyError):

    def __init__(self, response):
        super(ServerError, self).__init__(response, response.request.url, response.payload)


class ResponseHandler(object):

    deserializers = {
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

        raise ValueError("Unhandled response status %s" % r.status_code)

    def parse_payload(self, r):
        ct = r.headers.get("Content-Type").split(";", 1)[0]
        deserializer = self.deserializers.get(ct, None)
        if deserializer is None:
            r.payload = None
        else:
            r.payload = deserializer(self.session, r)

    def status_2xx(self, r):
        self.parse_payload(r)
        return r
    status_200 = status_2xx

    def status_201(self, r):
        # the caller will have to look up r.headers["Location"]
        return r

    status_204 = status_200

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
