import json
import threading
import sys
from unittest import TestCase

import pytest
import requests

from pycrunch import connect, connect_with_token, Session, __version__
from pycrunch.lemonpy import ServerError

try:
    from requests.packages.urllib3.response import HTTPResponse
except ImportError:
    from urllib3.response import HTTPResponse
try:
    from unittest import mock
except ImportError:
    import mock


@pytest.fixture(scope="module")
def http_server():
    import http.server
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/headers':
                reply = json.dumps({"headers":dict(self.headers)}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                reply = b"Not found"
            self.send_header('Content-Length', len(reply))
            self.end_headers()
            self.wfile.write(reply)

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    task = threading.Thread(target=server.serve_forever, daemon=True)
    task.start()
    yield server
    server.shutdown()
    server.server_close()
    task.join(timeout=1)


@pytest.mark.skipif(sys.version_info < (3, 4), reason="requires python 3.4 or higher")
def test_request_sends_user_agent(http_server):
    session = Session("not an email", "not a password", site_url="https://app.crunch.io/api/")
    url = "http://127.0.0.1:{}/headers".format(http_server.server_port)
    pycrunch_ua = 'pycrunch/%s' % __version__
    response = session.get(url)
    req_headers_sent = response.request.headers
    req_headers_received = response.json()['headers']
    assert 'user-agent' in req_headers_sent
    assert 'user-agent' in req_headers_received
    assert pycrunch_ua in req_headers_sent.get('user-agent', '')
    assert pycrunch_ua in req_headers_received.get('user-agent', '')


@pytest.mark.skipif(sys.version_info < (3, 4), reason="requires python 3.4 or higher")
def test_request_sends_gzip(http_server):
    session = Session("not an email", "not a password", site_url="https://app.crunch.io/api/")
    url = "http://127.0.0.1:{}/headers".format(http_server.server_port)
    response = session.get(url)
    req_headers_sent = response.request.headers
    req_headers_received = response.json()['headers']
    assert "gzip" in req_headers_sent['Accept-Encoding']
    assert "gzip" in req_headers_received['Accept-Encoding']


class TestHTTPResponses(TestCase):

    def test_response_with_no_content_type_header(self):
        # Simulate a 504 response with no Content-Type header and empty body.

        # pycrunch.lemonpy.ResponseHandler should be able to cope with this
        # peculiar situation.

        def _resp(adapter, request, *args, **kwargs):
            headers = {'Content-Length': '0'}
            response = HTTPResponse(status=504, body='', headers=headers)
            response = adapter.build_response(request, response)
            return response
        patch = mock.patch('requests.adapters.HTTPAdapter.send', _resp)

        patch.start()
        s = Session("not an email", "not a password", site_url="https://app.crunch.io/api/")
        with self.assertRaises(ServerError) as exc_info:
            s.get("http://httpbin.org/status/504")
        patch.stop()

        response = exc_info.exception.args[0]
        assert isinstance(response, requests.models.Response)
        self.assertEqual(response.status_code, 504)

    def test_401_handle_calls_proxies(self):
        sess = Session("not an email", "not a password", site_url="https://app.crunch.io/api/")
        headers = {'Set-Cookie': 'abx'}
        sess.post = lambda slf, *args, **kwargs: mock.MagicMock(headers=headers)
        sess.send = mock.MagicMock()
        url_401 = 'http://example.com/401'
        fake_request = mock.MagicMock(url=url_401)
        r = mock.MagicMock(
            request=fake_request,
            json=lambda: {'urls': {'login_url': 'http://www.httpbin.org/post'}}
        )

        from pycrunch.elements import ElementResponseHandler
        handler = ElementResponseHandler(sess)
        with mock.patch('pycrunch.elements.get_environ_proxies') as gep:
            gep.return_value = {}
            handler.status_401(r)
        gep.assert_called_once_with(url_401, no_proxy=None)
        sess.send.assert_called_with(fake_request, proxies={})


@pytest.fixture
def mock_sess():
    mock_sess = mock.MagicMock()
    mock_sess.return_value = {
        "https://us.crunch.io/api/": mock.MagicMock(payload="success"),
        "https://app.crunch.io/api/": mock.MagicMock(payload="success"),
    }
    return mock_sess


def test_connect(mock_sess):
    warnings = [
        "Please provide a site_url that includes your account's subdomain. This will soon be a requirement.",
        "Connecting to Crunch API services with a username and password will be removed soon. Please use connect(api_key=<key>, site_url=<site_url>).",
    ]

    with pytest.warns(DeprecationWarning) as warninfo:
        ret = connect(
            "me@mycompany.com",
            "yourpassword",
            session_class=mock_sess,
            site_url="https://app.crunch.io/api/",
        )

    warns = {(warn.category, warn.message.args[0]) for warn in warninfo}
    expected = {
        (DeprecationWarning, warnings[0]),
        (DeprecationWarning, warnings[1])
    }
    assert warns == expected
    assert ret == "success"
    mock_sess.assert_called_once_with(
        "me@mycompany.com",
        "yourpassword",
        progress_tracking=None,
        site_url="https://app.crunch.io/api/",
    )


def test_connect_with_api_key(mock_sess):
    ret = connect(
        "me@mycompany.com",
        "yourpassword",
        session_class=mock_sess,
        site_url="https://app.crunch.io/api/",
    )

    assert ret == "success"
    mock_sess.assert_called_once_with(
        "me@mycompany.com",
        "yourpassword",
        progress_tracking=None,
        site_url="https://app.crunch.io/api/",
    )


def test_connect_with_no_creds():
    with pytest.raises(RuntimeError) as err:
        connect()
    assert str(err.value) == "You must provide either a user and pw or an api_key"


def test_connect_with_token(mock_sess):
    """
    site_url will be required in the near future
    """
    warnings = [
        "connect_with_token will be removed soon. Please use connect(api_key=<key>, site_url=<site_url>) instead.",
        "Please provide a site_url that includes your account's subdomain. This will soon be a requirement.",
    ]

    with pytest.warns(DeprecationWarning) as warninfo:
        ret = connect_with_token("FOO", session_class=mock_sess)

    warns = {(warn.category, warn.message.args[0]) for warn in warninfo}
    expected = {
        (DeprecationWarning, warnings[0]),
        (DeprecationWarning, warnings[1])
    }
    assert warns == expected
    assert ret == "success"
    mock_sess.assert_called_once_with(
        token="FOO",
        site_url="https://app.crunch.io/api/",
        progress_tracking=None,
    )
