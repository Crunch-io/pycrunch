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
    dims = prepare_dims(dataset, dimensions)
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


def prepare_dims(dataset, dimensions):
    dims = []
    variables_by_alias = dataset.variables.by('alias')
    variables_by_name = dataset.variables.by('name')

    for dim in dimensions:
        if isinstance(dim, dict):
            # This is already a Crunch expression.
            dims.append(dim)
        elif isinstance(dim, six.string_types):
            if dim in dataset.variables.index:
                # When URL is provided, fetch variable from index
                dim = dataset.variables.index[dim]
            elif dim in variables_by_alias:
                dim = variables_by_alias[dim]
            elif dim in variables_by_name:
                dim = variables_by_name[dim]
            else:
                msg = "Can't find dim {} in dataset {}".format(dim, ds.self)
                raise ValueError(msg)
            dims.extend(prepare_ref(dim))
        else:
            msg = "dimensions must be URL strings or Crunch expression objects."
            raise TypeError(msg)

    return dims


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
