from unittest import TestCase

from pycrunch import Session, __version__

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
