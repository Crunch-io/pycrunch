from pandas import DataFrame, Categorical


def clean_item(item):
    try:
        item['?']
        return None
    except (TypeError, KeyError):
        return item

def clean_value(k, v, metadata=None):
    return [clean_item(item) for item in v]

def dataframe_from_dataset(site, dataset_name_or_id):

    try:
        dataset = site.datasets.by('name')[dataset_name_or_id]
    except KeyError:
        dataset = site.datasets.by('id')[dataset_name_or_id]

    t = dataset.entity.table
    data = {}

    for k, v in t.data.iteritems():
        metadata = t.metadata[k]
        value = clean_value(k, v, metadata)
        print metadata.name, metadata.type
        if metadata.type == 'categorical':
            cats = {cat['id']:cat['name'] for cat in metadata['categories']}
            value = [None if val is None else cats[val] for val in value]
            data[metadata.name] = Categorical(value,
                                              categories=[cat['name'] for cat in metadata['categories'] if not  cat['missing']],
                                              ordered=True)
            continue

        data[metadata.name] = value

    return DataFrame(data)
