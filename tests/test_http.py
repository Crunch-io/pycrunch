from unittest import TestCase

import requests
from pycrunch import Session, __version__
from pycrunch.lemonpy import ServerError

try:
    from requests.packages.urllib3.response import HTTPResponse
except ImportError:
    from urllib3.response import HTTPResponse
try:
    from unittest import mock
except ImportError:
    import mock


class TestHTTPRequests(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.s = Session("not an email", "not a password")
        cls.r = cls.s.get("http://httpbin.org/headers")

    def test_request_sends_user_agent(self):
        pycrunch_ua = 'pycrunch/%s' % __version__
        req_headers_sent = self.r.request.headers
        req_headers_received = self.r.json()['headers']
        self.assertTrue('user-agent' in req_headers_sent)
        self.assertTrue('User-Agent' in req_headers_received)
        self.assertTrue(pycrunch_ua in req_headers_sent.get('user-agent', ''))
        self.assertTrue(pycrunch_ua in req_headers_received.get('User-Agent', ''))

    def test_request_sends_gzip(self):
        req_headers_sent = self.r.request.headers
        req_headers_received = self.r.json()['headers']
        self.assertIn("gzip", req_headers_sent['Accept-Encoding'])
        self.assertIn("gzip", req_headers_received['Accept-Encoding'])


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
        s = Session("not an email", "not a password")
        with self.assertRaises(ServerError) as exc_info:
            s.get("http://httpbin.org/status/504")
        patch.stop()

        response = exc_info.exception.args[0]
        assert isinstance(response, requests.models.Response)
        self.assertEqual(response.status_code, 504)

    def test_401_handle_calls_proxies(self):
        sess = Session("not an email", "not a password")
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
