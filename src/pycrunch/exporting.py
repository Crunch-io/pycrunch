# coding: utf-8
import json
from .lemonpy import URL
from .shoji import wait_progress


def export_dataset(dataset, options, format='csv', progress_tracker=None):
    """
    Exports a Crunch dataset in the desired format. This is a blocking function
    call that will return a url where to download the exported file from.

    :param dataset: Shoji entity pointing to a Crnuch dataset
    :param options: Dictionary containing exporting options (where, filter, etc)
    :param format: Export format, CSV or SPSS
    :return: URL instance containing the url for the final file download
    """
    session = dataset.session
    endpoint = dataset.export.views[format]
    r = session.post(endpoint, json.dumps(options))
    dest_file = URL(r.headers['Location'], '')
    if r.status_code == 202:
        try:
            progress_url = r.payload['value']  # noqa
        except Exception:
            # Not a progress API just return the incomplete entity.
            # User will refresh it.
            pass
        else:
            # We have a progress_url, wait for completion
            wait_progress(r, session, progress_tracker)
    return dest_file
