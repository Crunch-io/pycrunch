from unittest import TestCase

from pycrunch import Session

class PycrunchTestCase(TestCase):
    
    def test_user_agent(self):
        s = Session("not an email", "not a password")
        r = s.get("http://httpbin.org/headers")
        req_headers_sent = r.request.headers
        req_headers_received = r.json()['headers']
        print req_headers_sent, req_headers_received
        self.assertTrue('user-agent' in req_headers_sent)
        self.assertTrue('User-Agent' in req_headers_received)
        self.assertTrue('pycrunch' in req_headers_sent.get('user-agent', ''))
        self.assertTrue('pycrunch' in req_headers_received.get('User-Agent', ''))
