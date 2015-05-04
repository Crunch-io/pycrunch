import mimetypes
import os
import time
import io

import six

from pycrunch import shoji


class Importer(object):

    def __init__(self, async=True, retries=40, frequency=0.25,
                 backoff_rate=1.1, backoff_max=30):
        self.async = async
        self.retries = retries
        self.frequency = frequency
        self.backoff_rate = backoff_rate
        self.backoff_max = backoff_max

    def wait_for_batch_status(self, batch, status):
        """Wait for the given status(es) and return the batch. Error if not reached."""
        if isinstance(status, six.string_types):
            status = [status]

        for trial in range(self.retries):
            new_batch = batch.session.get(batch.self).payload
            st = new_batch.body['status']
            if st in ('error', 'failed'):
                raise ValueError("The batch was not fully appended.")
            elif st == 'conflict':
                raise ValueError("The batch had conflicts.")
            elif st in status:
                return new_batch
            else:
                time.sleep(self.frequency)
                if self.frequency < self.backoff_max:
                    self.frequency *= self.backoff_rate
                    if self.frequency > self.backoff_max:
                        self.frequency = self.backoff_max
        else:
            raise ValueError("The batch did not reach the '%s' state in the "
                             "given time. Please check again later." % status)

    def append_csv_string(self, ds, csv_string, filename=None):
        """Append the given string of CSV data to the dataset. Return its Batch."""
        if filename is None:
            filename = 'upload.csv'
        fp = io.BytesIO(csv_string)
        source_url = self.add_source(ds, filename, fp, "text/csv")
        return self.create_batch_from_source(ds, source_url)

    def append_stream(self, ds, fp, filename=None, mimetype=None):
        """Append the given file-like object to the dataset. Return its Batch."""
        if filename is None:
            filename = 'upload.crunch'

        if mimetype is None:
            mimetype, encoding = mimetypes.guess_type(filename)

        source_url = self.add_source(ds, filename, fp, mimetype)
        return self.create_batch_from_source(ds, source_url)

    def append_file(self, ds, path, filename=None, mimetype=None):
        """Append the file at the given path to the dataset. Return its Batch."""
        if filename is None:
            filename = path.rsplit(os.path.sep, 1)[-1]

        if mimetype is None:
            mimetype, encoding = mimetypes.guess_type(filename)

        source_url = self.add_source(ds, filename, open(path, 'rb'), mimetype)
        return self.create_batch_from_source(ds, source_url)

    def add_source(self, ds, filename, fp, mimetype):
        """Create a new Source on the given dataset and return its URL."""
        sources_url = ds.user_url.catalogs['sources']
        # Don't call Catalog.post here (which would force application/json);
        # we want requests.Session to set multipart/form-data with a boundary.
        return ds.session.post(
            sources_url, files={"uploaded_file": (filename, fp, mimetype)}
        ).headers["Location"]

    def create_batch_from_source(self, ds, source_url, workflow=None, async=False):
        """Create and return a Batch on the given dataset for the given source."""
        batch = shoji.Entity(ds.session, body={
            'source': source_url,
            'workflow': workflow or [],
            'async': async,
        })
        ds.batches.create(batch)

        if async:
            # Wait for the batch to be ready...
            batch = self.wait_for_batch_status(batch, ['ready', 'imported'])
            if batch.body.status == 'ready':
                # Two-stage behavior: Tell the batch to start appending.
                batch_part = shoji.Entity(batch.session, body={'status': 'importing'})
                batch.patch(data=batch_part.json)

                # Wait for the batch to be imported...
                batch = self.wait_for_batch_status(batch, 'imported')
        else:
            batch.refresh()
            if batch.body.status == 'ready':
                # Two-stage behavior: Tell the batch to start appending.
                batch_part = shoji.Entity(batch.session, body={'status': 'importing'})
                batch.patch(data=batch_part.json)
                batch.refresh()

        return batch

    def create_batch_from_csv_file(self, ds, csv_file):
        """Create and return a Batch from the given CSV string or open file.

        This is commonly combined with csvlib to send rows of Python values
        as efficiently as possible:

            >>> rows = get_my_row_iterator()
            >>> f = csvlib.rows_as_csv_file(rows)
            >>> importer.create_batch_from_csv_file(ds, f)
        """
        ds.session.post(
            ds.batches.self,
            files={"file": ('content.csv', csv_file, 'text/csv')}
        )


importer = Importer()
"""A default Importer."""


def place(dataset, key, ids, data):
    """Place the given data into the dataset at the ids of the given key.

    The 'dataset' must be a Dataset entity (with a 'table' fragment).
    The 'key' must be an id or ZCL reference to a Variable in the dataset
    which possesses unique values. The items in the "ids" list will be looked
    up in this key and the matching rows will be written to.

    The 'data' argument must be a list of the same length as the 'ids' list;
    each row of data is written to each matching id. Each item in the 'data'
    list must be a dict mapping variable.ids to each new value. The values
    must be in the Crunch I/O format (i.e., integer ids for Categorical,
    ISO 8601 format for Datetime, etc.).

    Example:
        aliases = ds.variables.by("alias")
        place(
            ds,
            key=aliases["ID"].id,
            ids=[1, 13, 7],
            data=[
                {aliases["Gender"].id: 1, aliases["birthyear"].id: 1982},
                {aliases["Gender"].id: 1},
                {aliases["birthyear"].id: 1986},
            ]
        )

    On success, this returns None, otherwise, an error is raised.
    """
    if isinstance(key, six.string_types):
        key = {"variable": key}
    elif isinstance(key, dict):
        pass
    else:
        raise TypeError("The 'key' argument to place MUST be a string id "
                        "or a ZCL reference (a dict).")

    dataset.table.post({
        "command": "place",
        "key": key,
        "ids": {
            "column": ids,
            "type": {"function": "typeof", "args": [key]}
        },
        "data": data
    })
