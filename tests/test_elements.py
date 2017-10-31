import mock
from unittest import TestCase

import requests

from pycrunch import elements


class TestJSONObject(TestCase):

    class Foo(elements.JSONObject):
        pass

    def test_json_property(self):
        foo = self.Foo(bar=42)
        expected = '{\n    "bar": 42\n}'
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

    def test_follow(self):
        pass  # TODO

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
