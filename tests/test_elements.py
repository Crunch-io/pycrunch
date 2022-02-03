import mock
from unittest import TestCase

import requests

from pycrunch import elements, shoji

try:
    # Python 2
    from urllib import urlencode, quote
except ImportError:
    # Python 3
    from urllib.parse import urlencode, quote


class TestJSONObject(TestCase):

    class Foo(elements.JSONObject):
        pass

    def test_json_property(self):
        foo = self.Foo(bar=42)
        expected = '{\n    "bar": 42\n}'
        self.assertEqual(foo.pretty, expected)
        expected = '{"bar":42}'
        self.assertEqual(foo.json, expected)

    def test_str(self):
        foo = self.Foo(bar=42)
        expected = 'tests.test_elements.Foo(**{\n    "bar": 42\n})'
        self.assertEqual(str(foo), expected)

    def test_attribute_access(self):
        foo = self.Foo(bar=42)
        self.assertEqual(foo.bar, 42)

    def test_attribute_error(self):
        foo = self.Foo(bar=42)
        msg = 'Foo has no attribute nope'
        self.assertRaisesRegexp(AttributeError, msg, getattr, foo, 'nope')

    def test_copy(self):
        foo = self.Foo(bar=42)
        self.assertEqual(foo.copy(), {'bar': 42})


class TestElement(TestCase):

    class Foo(elements.Element):
        element = "shoji:foo"

    def test_copy(self):
        foo = self.Foo(session=None, bar=42)
        self.assertEqual(foo.copy(), {'bar': 42, 'element': 'shoji:foo'})


class TestParseElement(TestCase):

    class Shape(elements.Element):
        element = "shoji:shape"

    def test_unknown_element(self):
        # data dict should stay a dict because Color is unregistered
        data = {'name': 'blue', 'element': 'shoji:color'}
        result = elements.parse_element(session=None, j=data)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result, data)

    def test_dict(self):
        # data dict should become a Shape instance
        data = {'name': 'circle', 'element': 'shoji:shape'}
        result = elements.parse_element(session=None, j=data)
        self.assertTrue(isinstance(result, self.Shape))
        self.assertEqual(result, data)

    def test_list_of_dicts(self):
        # each dict in the data list should become a Shape instance
        data = [
            {'name': 'circle', 'element': 'shoji:shape'},
            {'name': 'square', 'element': 'shoji:shape'},
        ]
        result = elements.parse_element(session=None, j=data)
        for element in result:
            self.assertTrue(isinstance(element, self.Shape))
        self.assertEqual(result, data)


class TestDocument(TestCase):

    class Person(elements.Document):
        element = "shoji:person"

    def _mkresp(self, **attrs):
        resp = requests.Response()
        for n in attrs:
            setattr(resp, n, attrs[n])
        return resp

    def _mk_follow_doc(self, catalog_url):
        session = mock.MagicMock()
        resp = shoji.Catalog(session, **{
            "element": "shoji:catalog",
            "self": catalog_url
        })
        session.get = mock.MagicMock(return_value=self._mkresp(payload=resp))

        entity = shoji.Entity(session, **{
            "element": "shoji:entity",
            "self": "self/url",
            'body': {},
            'catalogs': {
                'follow_me': catalog_url
            }
        })
        return entity

    def test_follow(self):
        catalog_url = '/catalog/url/'
        entity = self._mk_follow_doc(catalog_url)
        self.assertEqual(entity.follow("follow_me").self, catalog_url)

    def test_follow_qs_as_dict(self):
        catalog_url = '/catalog/url/'
        entity = self._mk_follow_doc(catalog_url)
        query = {
            "param1": "value1",
            "param2": "value2",
        }
        entity.follow("follow_me", query)
        headers = {"Accept": "application/json, */*"}
        entity.session.get.assert_called_with("%s?%s" % (catalog_url, urlencode(query)), headers=headers)

    def test_follow_qs_as_string(self):  # This is the old way of using .follow
        catalog_url = '/catalog/url/'
        entity = self._mk_follow_doc(catalog_url)

        # Note that the query is a urlencoded string
        query = urlencode({
            "param1": "value1",
            "param2": "value2",
        })
        entity.follow("follow_me", query)
        headers = {"Accept": "application/json, */*"}
        entity.session.get.assert_called_with("%s?%s" % (catalog_url, query), headers=headers)

    def test_follow_uri_template(self):
        catalog_url = '/catalog/{name}/'
        entity = self._mk_follow_doc(catalog_url)

        # Note that the query is a urlencoded string
        query = {
            "param1": "value1",
            "param2": "value2",
            "name": "replaced/evil name"
        }
        entity.follow("follow_me", query)
        call_url = "%s?%s" % (catalog_url.replace("{name}", quote(query['name'], safe="")), urlencode({
            "param1": "value1",
            "param2": "value2"
        }))
        headers = {"Accept": "application/json, */*"}
        entity.session.get.assert_called_with(call_url, headers=headers)

    def test_follow_no_link(self):
        person = self.Person(session=None, self='some uri')
        msg = 'Person has no link foo'
        self.assertRaisesRegexp(AttributeError, msg, person.follow, 'foo')

    def test_refresh(self):
        before = {
            'old_field': 'should remove',
            'self': 'some uri', 'element': 'shoji:person'
        }
        after = {
            'new_field': 'should exist',
            'self': 'some uri', 'element': 'shoji:person'
        }

        session_mock = mock.MagicMock()
        response = self._mkresp(payload=after)
        session_mock.get = mock.MagicMock(return_value=response)

        person = self.Person(
            session=session_mock,
            self='some uri',
            old_field='should remove'
        )
        self.assertEqual(person, before)

        person.refresh()
        self.assertEqual(person, after)
        session_mock.get.assert_called_once_with('some uri')

    def test_refresh_no_response(self):
        session_mock = mock.MagicMock()
        response = self._mkresp(payload=None)
        session_mock.get = mock.MagicMock(return_value=response)

        person = self.Person(session=session_mock, self='some uri')
        msg = 'Response could not be parsed.'
        self.assertRaisesRegexp(TypeError, msg, person.refresh)
        session_mock.get.assert_called_once_with('some uri')

    def test_post(self):
        session_mock = mock.MagicMock()
        person = self.Person(session=session_mock, self='some uri')
        person.post(data={'age': 10})
        session_mock.post.assert_called_once_with(
            'some uri',
            '{"age": 10}',
            headers={'Content-Type': 'application/json'}
        )

    def test_put(self):
        session_mock = mock.MagicMock()
        person = self.Person(session=session_mock, self='some uri')
        person.put(data={'age': 10})
        session_mock.put.assert_called_once_with(
            'some uri',
            '{"age": 10}',
            headers={'Content-Type': 'application/json'}
        )

    def test_patch(self):
        session_mock = mock.MagicMock()
        person = self.Person(session=session_mock, self='some uri')
        person.patch(data={'age': 10})
        session_mock.patch.assert_called_once_with(
            'some uri',
            '{"age": 10}',
            headers={'Content-Type': 'application/json'}
        )

    def test_delete(self):
        session_mock = mock.MagicMock()
        person = self.Person(session=session_mock, self='some uri')
        person.delete()
        session_mock.delete.assert_called_once_with('some uri')
