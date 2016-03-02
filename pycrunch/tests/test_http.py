from unittest import TestCase

import pytest
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


class PycrunchTestCase(TestCase):
    
    def test_user_agent(self):
        pycrunch_ua = 'pycrunch/%s' % __version__
        s = Session("not an email", "not a password")
        r = s.get("http://httpbin.org/headers")
        req_headers_sent = r.request.headers
        req_headers_received = r.json()['headers']
        self.assertTrue('user-agent' in req_headers_sent)
        self.assertTrue('User-Agent' in req_headers_received)
        self.assertTrue(pycrunch_ua in req_headers_sent.get('user-agent', ''))
        self.assertTrue(pycrunch_ua in req_headers_received.get('User-Agent', ''))

    def test_response_with_no_content_type_header(self):
        """
        Simulate a 504 response with no Content-Type header and empty body.

        pycrunch.lemonpy.ResponseHandler should be able to cope with this
        peculiar situation.
        """

        def _resp(adapter, request, *args, **kwargs):
            headers = {'Content-Length': '0'}
            response = HTTPResponse(status=504, body='', headers=headers)
            response = adapter.build_response(request, response)
            return response
        patch = mock.patch('requests.adapters.HTTPAdapter.send', _resp)

        patch.start()
        s = Session("not an email", "not a password")
        with pytest.raises(ServerError) as exc_info:
            s.get("http://httpbin.org/status/504")
        patch.stop()

        response = exc_info.value.args[0]
        assert isinstance(response, requests.models.Response)
        self.assertEqual(response.status_code, 504)
