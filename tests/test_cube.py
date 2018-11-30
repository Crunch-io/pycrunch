from mock import Mock, patch
import pytest

from pycrunch.cubes import DimensionsPreparer


def test_prepare_ref(prepare_ref_fixture):
    dim, expected = prepare_ref_fixture
    actual = DimensionsPreparer.prepare_ref(dim)
    assert actual == expected


def test_get_dimension_by_string(dimension_string_fixture):
    dim_str, preparer, dim = dimension_string_fixture
    assert preparer.get_dimension_by_string(dim_str) == dim


# fixtures -----------------------------------------------------------


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

@pytest.fixture(params=[
    ('fake_url', 'URL', Mock(), None),
    ('fake_url/subvariables/fake_id', 'URL_SUBVAR', Mock(), Mock()),
    ('fake_alias', 'ALIAS', Mock(), None),
    ('fake_alias', 'NAME', Mock(), None),
])
def dimension_string_fixture(request):
    dim_str, str_type, dim, subvar = request.param
    preparer = DimensionsPreparer(Mock())
    preparer._dataset.variables.index = dict()
    preparer._variables_by_alias = dict()
    preparer._variables_by_name = dict()
    if str_type == 'URL':
        preparer._dataset.variables.index[dim_str] = dim
    elif str_type == 'URL_SUBVAR':
        var_url = dim_str.split('subvariables/')[0]
        preparer._dataset.variables.index[var_url] = dim
        preparer._dataset.variables.index[
            var_url
        ].entity.subvariables.index = {dim_str: subvar}
        dim = subvar
    elif str_type == 'ALIAS':
        preparer._variables_by_alias[dim_str] = dim
    elif str_type == 'NAME':
        preparer._variables_by_name[dim_str] = dim
    return dim_str, preparer, dim
