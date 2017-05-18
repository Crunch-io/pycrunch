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
    dims = []
    for d in dimensions:
        if isinstance(d, dict):
            # This is already a Crunch expression.
            dims.append(d)
        elif isinstance(d, six.string_types):
            ref = {'variable': d}
            # A URL of a variable entity. GET it to find its type.
            v = dataset.session.get(d).payload
            if v.body.type == "numeric":
                dims.append({"function": "bin", "args": [ref]})
            elif v.body.type == "datetime":
                rollup_res = v.body.view.get("rollup_resolution", None)
                dims.append({"function": "rollup", "args": [ref, {"value": rollup_res}]})
            elif v.body.type == "categorical_array":
                dims.append({"each": d})
                dims.append(ref)
            elif v.body.type == "multiple_response":
                dims.append({"each": d})
                dims.append({"function": "as_selected", "args": [ref]})
            else:
                dims.append(ref)
        else:
            raise TypeError("dimensions must be URL strings or Crunch expression objects.")

    q = elements.JSONObject(dimensions=dims, measures=measures)
    if weight is not None:
        q['weight'] = weight

    params = {"query": q.json}
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
