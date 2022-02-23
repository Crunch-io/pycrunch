"""Functions for manipulating crunch cubes."""

import six

from pycrunch import elements


def fetch_cube(dataset, dimensions, weight=None, filter=None, **measures):
    """Return a shoji.View containing a crunch:cube.

    The dataset entity is used to look up its views.cube URL.
    The dimensions must be a list of either strings, which are assumed to be
    URL's of variable Entities to be fetched and analyzed according to type,
    or objects, which are assumed to be complete variable expressions.
    The weight, if sent, should be the URL of a valid weight variable
    If applying a filter, it should be a filter expression or filter URL.

    >>> dataset = session.site.datasets.by('name')['my dataset'].entity
    >>> variables = dataset.variables.by('alias')
    >>> dimensions = [
    ... {"each": variables['CA'].entity_url},
    ...     {"variable": variables['CA'].entity_url}
    ... ]
    >>> weight = variables['weight_var'].entity_url
    >>> count = {
    ...     "function": "cube_count",
    ...     "args": []
    ... }
    >>> filter = {
    ...     "function": "!=",
    ...     "args": [
    ...         {"variable": variables['categorical_var'].entity_url},
    ...         {"value": 3},
    ...     ]
    ... }
    >>> fetch_cube(dataset, dimensions, weight=weight, filter=filter, count=count)

    """
    dims = DimensionsPreparer(dataset).prepare_dimensions(dimensions)
    cube_query = elements.JSONObject(dimensions=dims, measures=measures)

    if weight is not None:
        cube_query['weight'] = weight

    params = {"query": cube_query.json}
    if filter is not None:
        params['filter'] = elements.JSONObject(filter).json

    return dataset.session.get(
        dataset.views.cube,
        params=params
    ).payload


class DimensionsPreparer(object):

    """Implement basic preparation of requested cube dimensions.

    Cube dimensions can be requested in different forms:

    1. Crunch expressions
    2. Variable URLs (or full Subvariable URLs)
    3. Variable Names
    4. Variable Aliases

    If Crunch expression is provided, no action needs to be taken, because the
    cube api can handle this notation. In the case of URLs, names, or aliases,
    the conversion needs to be done (to crunch expression), in order for cube
    api to be able to handle it.
    """

    def __init__(self, dataset):
        # If dataset has not fetched from the API, do it now.
        if not hasattr(dataset, "catalogs"):
            dataset.refresh()
        self._dataset = dataset
        self._variables_by_alias = dataset.variables.by('alias')
        self._variables_by_name = dataset.variables.by('name')

    def prepare_dimensions(self, dimensions):
        """Return list of crunch expressions for each cube dimension.

        :param dimensions: Collection of cube dimensions (as Crunch
            expressions, URLs, Names, or Aliases')
        :type dimensions: list of strings or dicts
        """

        dims = []

        for dim in dimensions:
            if isinstance(dim, dict):
                # This is already a Crunch expression.
                dims.append(dim)
            elif isinstance(dim, six.string_types):
                dim = self.get_dimension_by_string(dim)
                dims.extend(self.prepare_ref(dim))
            else:
                raise TypeError(
                    "Dimensions must be URL strings "
                    "or Crunch expression objects."
                )

        return dims

    def get_dimension_by_string(self, dim_str):
        """Return variable object from pycrunch dataset.

        :param dim_str: String representing URL, Name, or Alias of a variable
        """

        if dim_str in self._dataset.variables.index:
            # When URL is provided, fetch variable from index
            return self._dataset.variables.index[dim_str]
        elif dim_str in self._variables_by_alias:
            return self._variables_by_alias[dim_str]
        elif dim_str in self._variables_by_name:
            return self._variables_by_name[dim_str]
        elif 'subvariables/' in dim_str:
            var_url = dim_str.split('subvariables/')[0]
            variable = self._dataset.variables.index[var_url]
            return variable.entity.subvariables.index[dim_str]

        raise ValueError("Can't find variable {} in dataset {}".format(
            dim_str, self._dataset.self
        ))


    @staticmethod
    def prepare_ref(dim):
        ref = {'variable': dim.entity_url}
        if dim.type == "numeric":
            ref = [{"function": "bin", "args": [ref]}]
        elif dim.type == "datetime":
            rollup_res = dim.rollup_resolution
            ref = [{"function": "rollup", "args": [ref, {"value": rollup_res}]}]
        elif dim.type == "categorical_array":
            ref = [{"each": dim.entity_url}, ref]
        elif dim.type == "multiple_response":
            ref = [{"each": dim.entity_url}, {"function": "as_selected", "args": [ref]}]
        else:
            ref = [ref]

        return ref


def count(*args):
    return {"function": "cube_count", "args": list(args)}
