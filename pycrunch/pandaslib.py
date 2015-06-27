from pandas import DataFrame, Categorical, Series, to_datetime


def series_from_variable(value, metadata):
    value = [None if (isinstance(item, dict) and item.keys() == ['?']) else item for item in value]

    type_ = metadata.type

    if type_ == 'categorical':
        cats = {cat['id']:cat['name'] for cat in metadata['categories']}
        value = [None if val is None else cats[val] for val in value]
        return Categorical(value,
                           categories=[cat['name'] for cat in metadata['categories'] if not cat['missing']],
                           ordered=True)

    if type_ == 'datetime':
        return to_datetime(Series(value))

    return Series(value)


def dataframe_from_dataset(site, dataset_name_or_id, variables=None):

    try:
        dataset = site.datasets.by('name')[dataset_name_or_id]
    except KeyError:
        dataset = site.datasets.by('id')[dataset_name_or_id]

    data = {}

    if variables is None:

        t = dataset.entity.table
        metadata = t.metadata

        for name, value in t.data.iteritems():
            vardef = t.metadata[name]
            data[vardef.alias] = series_from_variable(value, vardef)

    else:
        metadata = {}
        if not isinstance(variables, list):
            variables = list(variables)

        for variable in variables:
            try:
                t = dataset.entity.variables.by('name')[variable].entity
            except KeyError:
                raise KeyError('No variable with name: %s' % variable)
            vardef = t.body
            value = t.values_url.value
            data[vardef.alias] = series_from_variable(value, vardef)
            metadata[vardef.id] = vardef

    df = DataFrame(data)

    # Attach the crunch:table metadata object to the df
    # so consumers can have both.
    df.metadata = metadata

    return df
