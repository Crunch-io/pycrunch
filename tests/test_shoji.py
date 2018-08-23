# -*- coding: utf-8 -*-
import json

import mock
from six.moves.urllib_parse import urljoin
from unittest import TestCase

import sys
from requests import Response

from pycrunch.progress import DefaultProgressTracking, SimpleTextBarProgressTracking
from pycrunch.shoji import Catalog, TaskProgressTimeoutError, TaskError, Index, Order, Entity
from pycrunch.lemonpy import URL


class TestShojiCreation(TestCase):
    def _mkresp(self, **attrs):
        resp = Response()
        for n in attrs:
            setattr(resp, n, attrs[n])
        return resp

    def test_create_does_post_catalog(self):
        sess = mock.MagicMock()
        c = Catalog(self='http://host.com/catalog', session=sess)
        c.create({'somedata': 1})
        sess.post.assert_called_once_with(
            'http://host.com/catalog',
            json.dumps({"somedata": 1, "body": {}, "element": "shoji:entity"}, indent=4),
            headers={'Content-Type': 'application/json'}
        )

    def test_create_does_post_entity(self):
        sess = mock.MagicMock()
        e = Entity(self='/entity/url/', session=sess)
        e.create({'somedata': 1})
        sess.post.assert_called_once_with(
            '/entity/url/',
            json.dumps({"somedata": 1, "body": {}, "element": "shoji:entity"}, indent=4),
            headers={'Content-Type': 'application/json'}
        )

    def test_create_waits_for_progress(self):
        sess = mock.MagicMock()
        sess.progress_tracking = DefaultProgressTracking(timeout=1.0, interval=0.1)
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
        sess.progress_tracking = DefaultProgressTracking(timeout=0.1, interval=0.1)
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
        self.assertRaises(TaskProgressTimeoutError, c.create, {'somedata': 1})

    def test_create_timesout_continuation(self):
        sess = mock.MagicMock()
        sess.progress_tracking = DefaultProgressTracking(timeout=0.1, interval=0.1)
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

        try:
            c.create({'somedata': 1})
        except TaskProgressTimeoutError as e:
            sess.progress_tracking = DefaultProgressTracking(timeout=None, interval=0.1)
            e.entity.wait_progress(e.response)
            self.assertEqual(sess.get.call_count, 3)
        else:
            assert False, "Should have raised TaskProgressTimeoutError"

    def test_create_raises_failures(self):
        sess = mock.MagicMock()
        sess.progress_tracking = DefaultProgressTracking(timeout=1.0, interval=0.1)
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

    def test_create_progressbar(self):
        sess = mock.MagicMock()
        sess.post = mock.MagicMock(return_value=self._mkresp(
            status_code=202,
            headers={'Location': 'http://host.com/somewhere'},
            payload={"value": 'http://host.com/progress/1'}
        ))
        sess.get = mock.MagicMock(side_effect=[
            self._mkresp(
                status_code=200,
                payload={'value': {'progress': i * 10}}
            ) for i in range(11)
        ])

        c = Catalog(self='http://host.com/catalog', session=sess)

        class FakeStdout(object):
            writes = []

            def write(self, text):
                self.writes.append(text)

            def flush(self):
                pass

        with mock.patch.object(sys, 'stdout', FakeStdout()):
            c.create(
                {'somedata': 1},
                progress_tracker=SimpleTextBarProgressTracking(
                    timeout=None, interval=0.1
                )
            )

        # Check we printed the progressbar up to 100%.
        self.assertEqual(''.join(FakeStdout.writes).count('-'),
                         SimpleTextBarProgressTracking.BAR_WIDTH)

    def test_accepts_document_instance(self):
        sess = mock.MagicMock()
        location = 'http://host.com/somewhere'
        sess.post = mock.MagicMock(return_value=self._mkresp(
            status_code=201,
            headers={'Location': location}
        ))
        catalog = Catalog(self='http://host.com/catalog', session=sess)
        body = {
            "name": 'subcatalog'
        }
        sub_catalog = Catalog(session=sess, body=body)
        retval = catalog.create(sub_catalog)
        self.assertEqual(retval.self, location)
        self.assertEqual(retval.body, body)


class TestIndex(TestCase):
    def test_relative_access(self):
        base_url = URL('http://host.name/base/url/', None)
        session = mock.MagicMock()

        rel_url = '../folder/item/'
        abs_url = URL(rel_url, base_url).absolute

        tup = {'id': 1}  # Some arbitrary value

        rel_index = Index(session, base_url, **{
            rel_url: tup
        })
        abs_index = Index(session, base_url, **{
            abs_url: tup
        })

        abs_on_rel = rel_index[abs_url]
        rel_on_abs = abs_index[rel_url]

        self.assertEqual(abs_on_rel, rel_on_abs)
        self.assertEqual(abs_on_rel, tup)
        self.assertEqual(rel_on_abs, tup)

    def test_catalog_follow_entity(self):
        base_url = URL('http://host.name/catalog/', None)

        ent_1_url = urljoin(base_url, '01/')
        ent_2_url = urljoin(base_url, '02/')
        ent_3_url = urljoin(base_url, '03/')
        ent_4_url = urljoin(base_url, '04/')
        entities = {
            ent_1_url: {
                'full_entity': True,
                'name': 'Ent 01'
            },
            ent_2_url: {
                'full_entity': True,
                'name': 'Ent 02'
            },
            ent_3_url: {
                'full_entity': True,
                'name': 'Ent 03'
            },
            ent_4_url: {
                'full_entity': True,
                'name': 'Ent 04'
            }
        }

        fetches = []

        def _get(ent_url, *args, **kwargs):
            fetches.append((ent_url, args, kwargs))
            resp = mock.Mock(payload=entities[ent_url])
            return resp

        session = mock.MagicMock()
        session.get = _get
        payload = {
            'element': 'shoji:catalog',
            'self': base_url,
            # This index has mixed urls as kes
            'index': {
                './01/': {
                    'name': '01'
                },
                ent_2_url: {
                    'name': '02'
                }
            }
        }

        index = Index(session, base_url, **payload['index'])
        # Continue growing the index using other ways, __setitem__ and .update
        index['03/'] = {  # This has another way of being valid relative
            'name': '03'
        }
        index.update({
            '../catalog/04/': {  # Yet way of being valid relative
                'name': '04'
            }
        })

        self.assertTrue(index[ent_1_url].entity['full_entity'])
        self.assertEqual(index[ent_1_url].entity['name'], 'Ent 01')
        self.assertTrue(index['01/'].entity['full_entity'])
        self.assertEqual(index['01/'].entity['name'], 'Ent 01')
        self.assertTrue(index['./01/'].entity['full_entity'])
        self.assertEqual(index['./01/'].entity['name'], 'Ent 01')
        self.assertTrue(index['../catalog/01/'].entity['full_entity'])
        self.assertEqual(index['../catalog/01/'].entity['name'], 'Ent 01')

        self.assertTrue(index[ent_2_url].entity['full_entity'])
        self.assertEqual(index[ent_2_url].entity['name'], 'Ent 02')
        self.assertTrue(index['02/'].entity['full_entity'])
        self.assertEqual(index['02/'].entity['name'], 'Ent 02')
        self.assertTrue(index['./02/'].entity['full_entity'])
        self.assertEqual(index['./02/'].entity['name'], 'Ent 02')
        self.assertTrue(index['../catalog/02/'].entity['full_entity'])
        self.assertEqual(index['../catalog/02/'].entity['name'], 'Ent 02')

        self.assertTrue(index[ent_3_url].entity['full_entity'])
        self.assertEqual(index[ent_3_url].entity['name'], 'Ent 03')
        self.assertTrue(index['03/'].entity['full_entity'])
        self.assertEqual(index['03/'].entity['name'], 'Ent 03')
        self.assertTrue(index['./03/'].entity['full_entity'])
        self.assertEqual(index['./03/'].entity['name'], 'Ent 03')
        self.assertTrue(index['../catalog/03/'].entity['full_entity'])
        self.assertEqual(index['../catalog/03/'].entity['name'], 'Ent 03')

        self.assertTrue(index[ent_4_url].entity['full_entity'])
        self.assertEqual(index[ent_4_url].entity['name'], 'Ent 04')
        self.assertTrue(index['04/'].entity['full_entity'])
        self.assertEqual(index['04/'].entity['name'], 'Ent 04')
        self.assertTrue(index['./04/'].entity['full_entity'])
        self.assertEqual(index['./04/'].entity['name'], 'Ent 04')
        self.assertTrue(index['../catalog/04/'].entity['full_entity'])
        self.assertEqual(index['../catalog/04/'].entity['name'], 'Ent 04')

        self.assertEqual(fetches, [
            (ent_1_url, (), {}),
            (ent_2_url, (), {}),
            (ent_3_url, (), {}),
            (ent_4_url, (), {}),
        ])


class TestOrders(TestCase):
    def test_follows_catalogs(self):
        catal_url = '/catalog/url/'
        session = mock.Mock(**{
            'get': lambda x: mock.Mock(**{'payload.self': catal_url})
        })

        order = Order(session, **{
            'graph': [],
            'catalogs': {
                'follow_me': catal_url
            }
        })
        self.assertEqual(order.follow_me.self, catal_url)


class TestEntities(TestCase):
    def test_entities_can_have_index(self):
        ent_url = '/entity/url/'
        session = mock.Mock()
        body = {
            'attr': 'val'
        }
        index = {
            'url1/': {'key': 'val1'},
            'url2/': {'key': 'val2'}
        }
        ent = Entity(session, **{
            'self': ent_url,
            'body': body,
            'index': index
        })
        self.assertTrue(isinstance(ent.index, Index))
        self.assertEqual(ent.by('key')['val1'].entity_url, 'url1/')
