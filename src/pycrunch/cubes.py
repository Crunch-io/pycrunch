"""Functions for manipulating crunch cubes."""

import six

from pycrunch import elements
from requests.exceptions import MissingSchema

from cr.cube.crunch_cube import CrunchCube


def crtabs(dataset, variables):
    """Return CrunchCube representation of crosstab.

    :param dataset: Dataset shoji object
    :param variables: List of variable urls, names or aliases
    """
    return CrunchCube(fetch_cube(dataset, variables, count=count()))


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
    dims = []
    variables_alias = dataset.variables.by('alias')
    variables_name = dataset.variables.by('name')
    for dim in dimensions:
        if isinstance(dim, dict):
            # This is already a Crunch expression.
            dims.append(dim)
        elif isinstance(dim, six.string_types):
            # A URL of a variable entity. GET it to find its type.
            try:
                var = dataset.session.get(dim).payload
            except MissingSchema:
                try:
                    dim = variables_alias[dim].entity_url
                    var = dataset.session.get(dim).payload
                except KeyError:
                    # Try to find variables by name
                    dim = variables_name[dim].entity_url
                    var = dataset.session.get(dim).payload

            ref = {'variable': dim}
            if var.body.type == "numeric":
                dims.append({"function": "bin", "args": [ref]})
            elif var.body.type == "datetime":
                rollup_res = var.body.view.get("rollup_resolution", None)
                dims.append({"function": "rollup", "args": [ref, {"value": rollup_res}]})
            elif var.body.type == "categorical_array":
                dims.append({"each": dim})
                dims.append(ref)
            elif var.body.type == "multiple_response":
                dims.append({"each": dim})
                dims.append({"function": "as_selected", "args": [ref]})
            else:
                dims.append(ref)
        else:
            msg = "dimensions must be URL strings or Crunch expression objects."
            raise TypeError(msg)

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


class Cube(elements.Element):
    """A crunch:cube: the result of calculating measures over dimensions."""

    element = "crunch:cube"


def count(*args):
    return {"function": "cube_count", "args": list(args)}


count.result = lambda data, n_missing: {
    "data": data,
    "n_missing": n_missing,
    "metadata": {
        "derived": True,
        "references": {},
        "type": {
            "integer": True,
            "class": "numeric",
            "missing_rules": {},
            "missing_reasons": {"No Data": -1}
        }
    }
}
