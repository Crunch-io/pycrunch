from pandas import DataFrame, Categorical, Series, to_datetime


def series_from_variable(value, metadata):
    value = [None if (isinstance(item, dict) and item.keys() == ['?']) else item for item in value]

    type_ = metadata.type
    if type == 'categorical':
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

        for name, value in t.data.iteritems():
            metadata = t.metadata[name]
            data[metadata.name] = series_from_variable(value, metadata)

    else:
        if not isinstance(variables, list):
            variables = list(variables)

        for variable in variables:
            try:
                t = dataset.entity.variables.by('name')[variable].entity
            except KeyError:
                raise KeyError('No variable with name: %s' % variable)
            metadata = t.body
            value = t.values_url.value
            data[metadata.name] = series_from_variable(value, metadata)

    return DataFrame(data)
