from mock import Mock
import pytest

from pycrunch.cubes import prepare_ref


def test_prepare_ref(prepare_ref_fixture):
    dim, expected = prepare_ref_fixture
    actual = prepare_ref(dim)
    assert actual == expected


@pytest.fixture(params=[
    ('categorical', None, [{'variable': 'fake_url'}]),
    ('numeric', None, [{'function': 'bin', 'args': [{'variable': 'fake_url'}]}]),
    ('datetime', 'fake_rollup', [{'function': 'rollup', 'args': [{'variable': 'fake_url'}, {'value': 'fake_rollup'}]}]),
    ('datetime', None, [{'function': 'rollup', 'args': [{'variable': 'fake_url'}, {'value': None}]}]),
    ('multiple_response', None, [{'each': 'fake_url'}, {'function': 'as_selected', 'args': [{'variable': 'fake_url'}]}]),
])
def prepare_ref_fixture(request):
    dimension_type, rollup, expected = request.param
    dim = Mock(entity_url='fake_url')
    dim.type = dimension_type
    dim.rollup_resolution = rollup
    return dim, expected
