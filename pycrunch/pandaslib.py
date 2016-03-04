import six
from pandas import DataFrame, Categorical, Series, to_datetime


def series_from_variable(col, vardef):
    """Return the given Crunch column and variable def as a Pandas Series."""
    col = [None if (isinstance(item, dict) and list(item.keys()) == ['?']) else item
           for item in col]

    if vardef.type == 'categorical':
        cats = dict((c['id'], c['name']) for c in vardef['categories'])
        col = [None if val is None else cats[val] for val in col]
        return Categorical(
            col,
            categories=[cat['name'] for cat in vardef['categories']
                        if not cat['missing']],
            ordered=True
        )
    elif vardef.type == 'datetime':
        return to_datetime(Series(col))

    return Series(col)


ROWCHUNKSIZE = 1000


def dataframe(dataset, variables=None):
    """Return a Pandas DataFrame for the given Crunch Dataset Entity object.
    Retrieve a dataset using pycrunch.get_dataset("dataset name or id").

    If the 'variables' argument is given and not None, it should be a
    single variable alias, or a list of such, in which case only those
    variables will be included in the DataFrame. If omitted or None,
    all variables are included.

    The returned DataFrame has an extra "metadata" attribute on it:
    a dict of Crunch variable definitions for each Series (keyed by id).
    """
    data = {}

    if variables is None:
        numrows = dataset.summary.value.unweighted.total
        seenrows = 0
        all_data = {}
        while True:
            t = dataset.session.get(
                "%s?offset=%d&limit=%d" %
                (dataset.fragments['table'], seenrows, ROWCHUNKSIZE)
            ).payload
            for name, value in six.iteritems(t.data):
                if name not in all_data:
                    all_data[name] = []
                all_data[name].extend(value)
            seenrows += ROWCHUNKSIZE
            if seenrows > numrows:
                break

        metadata = t.metadata

        # Convert to Series
        for varid, col in six.iteritems(all_data):
            vardef = t.metadata[varid]
            data[vardef.alias] = series_from_variable(col, vardef)
    else:
        metadata = {}
        if not isinstance(variables, list):
            variables = list(variables)

        var_catalog = dataset.variables
        for variable in variables:
            try:
                t = var_catalog.by('alias')[variable].entity
            except KeyError:
                raise KeyError('No variable with alias: %s' % variable)
            vardef = t.body
            value = dataset.session.get(t.views['values']).payload['value']
            data[vardef.alias] = series_from_variable(value, vardef)
            metadata[vardef.id] = vardef

    df = DataFrame(data)

    # Attach the crunch:table metadata object to the df
    # so consumers can have both.
    df.metadata = metadata

    return df
