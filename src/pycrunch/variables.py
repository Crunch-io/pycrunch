from pycrunch import elements


def cast(variable, type, format=None, offset=None, resolution=None):
    """Alter the given variable Entity to a new type.

    Various parameters may need to be sent to properly convert from one type
    to another. Datetime is particularly demanding.
    """
    payload = elements.JSONObject(cast_as=type)
    if format is not None:
        payload['format'] = format
    if offset is not None:
        payload['offset'] = offset
    if resolution is not None:
        payload['resolution'] = resolution

    return variable.cast.post(data=payload.json)
