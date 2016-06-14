# -*- coding: utf-8 -*-
import json

import mock
from unittest import TestCase

from requests import Response

from pycrunch.shoji import Catalog, TaskProgressTimeoutError, TaskError


class TestShojiCreation(TestCase):
    def _mkresp(self, **attrs):
        resp = Response()
        for n in attrs:
            setattr(resp, n, attrs[n])
        return resp

    def test_create_does_post(self):
        sess = mock.MagicMock()
        c = Catalog(self='http://host.com/catalog', session=sess)

        c.create({'somedata': 1})

        sess.post.assert_called_once_with(
            'http://host.com/catalog',
            json.dumps({"somedata": 1, "body": {}, "element": "shoji:entity"}, indent=4),
            headers={'Content-Type': 'application/json'}
        )

    def test_create_waits_for_progress(self):
        sess = mock.MagicMock()
        sess.post = mock.MagicMock(return_value=self._mkresp(
            status_code=202,
            headers={'Location': 'http://host.com/somewhere'},
            payload={"value": 'http://host.com/progress/1'}
        ))
        sess.get = mock.MagicMock(side_effect=[
            self._mkresp(status_code=200, payload={'value': {'progress': 30}}),
            self._mkresp(status_code=200, payload={'value': {'progress': 60}}),
            self._mkresp(status_code=200, payload={'value': {'progress': 100}}),
        ])

        c = Catalog(self='http://host.com/catalog', session=sess)
        c.create({'somedata': 1})

        # Assert progress got called until it completed
        self.assertEqual(sess.get.call_count, 3)

    def test_create_timesout(self):
        sess = mock.MagicMock()
        sess.post = mock.MagicMock(return_value=self._mkresp(
            status_code=202,
            headers={'Location': 'http://host.com/somewhere'},
            payload={"value": 'http://host.com/progress/1'}
        ))
        sess.get = mock.MagicMock(side_effect=[
            self._mkresp(status_code=200, payload={'value': {'progress': 30}}),
            self._mkresp(status_code=200, payload={'value': {'progress': 60}}),
            self._mkresp(status_code=200, payload={'value': {'progress': 100}}),
        ])

        c = Catalog(self='http://host.com/catalog', session=sess)

        import pycrunch.shoji
        progress_timeout = pycrunch.shoji.DEFAULT_PROGRESS_TIMEOUT

        try:
            pycrunch.shoji.DEFAULT_PROGRESS_TIMEOUT = 0.1
            self.assertRaises(TaskProgressTimeoutError, c.create, {'somedata': 1})
        finally:
            pycrunch.shoji.DEFAULT_PROGRESS_TIMEOUT = progress_timeout

    def test_create_timesout_continuation(self):
        sess = mock.MagicMock()
        sess.post = mock.MagicMock(return_value=self._mkresp(
            status_code=202,
            headers={'Location': 'http://host.com/somewhere'},
            payload={"value": 'http://host.com/progress/1'}
        ))
        sess.get = mock.MagicMock(side_effect=[
            self._mkresp(status_code=200, payload={'value': {'progress': 30}}),
            self._mkresp(status_code=200, payload={'value': {'progress': 60}}),
            self._mkresp(status_code=200, payload={'value': {'progress': 100}}),
        ])

        c = Catalog(self='http://host.com/catalog', session=sess)

        import pycrunch.shoji
        progress_timeout = pycrunch.shoji.DEFAULT_PROGRESS_TIMEOUT

        try:
            pycrunch.shoji.DEFAULT_PROGRESS_TIMEOUT = 0.1
            c.create({'somedata': 1})
        except TaskProgressTimeoutError as e:
            e.entity.wait_progress(e.response)
            self.assertEqual(sess.get.call_count, 3)
        else:
            assert False, "Should have raised TaskProgressTimeoutError"
        finally:
            pycrunch.shoji.DEFAULT_PROGRESS_TIMEOUT = progress_timeout

    def test_create_raieses_failures(self):
        sess = mock.MagicMock()
        sess.post = mock.MagicMock(return_value=self._mkresp(
            status_code=202,
            headers={'Location': 'http://host.com/somewhere'},
            payload={"value": 'http://host.com/progress/1'}
        ))
        sess.get = mock.MagicMock(side_effect=[
            self._mkresp(status_code=200, payload={'value': {'progress': -1,
                                                             'message': 'Some Failure'}}),
        ])

        c = Catalog(self='http://host.com/catalog', session=sess)
        self.assertRaises(TaskError, c.create, {'somedata': 1})
