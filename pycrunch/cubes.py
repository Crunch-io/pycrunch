from pycrunch import elements


def fetch_cube(dataset, dimensions, **measures):
    """Return a shoji.View containing a crunch:cube."""
    dims = []
    for d in dimensions:
        # TODO: vary this by type
        ref = {'variable': d.url}
        dims.append(ref)

    return dataset.session.get(
        dataset.views.cube,
        params={"query": elements.JSONObject(dimensions=dims, measures=measures).json}
    ).payload


class Cube(elements.Element):

    element = "crunch:cube"
    navigation_collections = ()


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

# TODO: make this __meta__?
elements.elements["crunch:cube"] = Cube
