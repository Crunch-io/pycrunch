from pandas import DataFrame


def dataframe_from_dataset(site, dataset_name_or_id):

    try:
        dataset = site.datasets.by('name')[dataset_name_or_id]
    except KeyError:
        dataset = site.datasets.by('id')[dataset_name_or_id]

    df = DataFrame(dataset.entity.table)

    return df
