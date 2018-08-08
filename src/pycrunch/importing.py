import json
import mimetypes
import os
import time

import six

from pycrunch import shoji, csvlib


class Importer(object):
    """A class for collecting the various ways to import data into Crunch.

    If the 'strict' argument is omitted or None, then any given CSV file
    is expected to conform to any previous metadata provided; that is,
    it shall not contain any columns nor categories not previously defined.
    If 0, then any undefined columns present in the CSV are ignored,
    and any undefined category ids generate new "missing" categories
    with the given id.
    """

    def __init__(self, retries=40, frequency=0.25,
                 backoff_rate=1.1, backoff_max=30, strict=None,
                 progress_tracker=None):
        self.retries = retries
        self.frequency = frequency
        self.backoff_rate = backoff_rate
        self.backoff_max = backoff_max
        self.strict = strict
        self.progress_tracker = progress_tracker

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

    def add_source(self, ds, filename, fp, mimetype):
        """Create a new Source on the given dataset and return its URL."""
        sources_url = ds.user_url.catalogs['sources']
        # Don't call Catalog.post here (which would force application/json);
        # we want requests.Session to set multipart/form-data with a boundary.
        new_source_url = ds.session.post(
            sources_url, files={"uploaded_file": (filename, fp, mimetype)}
        ).headers["Location"]

        if self.strict is not None:
            r = ds.session.get(new_source_url)
            if r.payload is None:
                raise TypeError("Response could not be parsed.", r)
            source = r.payload

            settings = source.body.get("settings", {})
            settings['strict'] = self.strict
            source.edit(settings=settings)

        return new_source_url

    def create_batch_from_source(self, ds, source_url, workflow=None,
                                 savepoint=True, autorollback=True):
        """Create and return a Batch on the given dataset for the given source."""
        batch = shoji.Entity(ds.session, body={
            'source': source_url,
            'workflow': workflow or []
        }, savepoint=savepoint, autorollback=autorollback)
        return ds.batches.create(batch, progress_tracker=self.progress_tracker).refresh()

    def append_rows(self, ds, rows):
        """Append the given rows of Python values. Return the new Batch."""
        f = csvlib.rows_as_csv_file(rows)
        return self.append_csv_string(ds, f)
    # Deprecated spelling:
    create_batch_from_rows = append_rows

    def append_csv_string(self, ds, csv_file, filename=None):
        """Append the given CSV string or open file. Return its Batch."""
        if filename is None:
            filename = 'upload.csv'

        source_url = self.add_source(ds, filename, csv_file, 'text/csv')
        return self.create_batch_from_source(ds, source_url)
    # Deprecated spellings:
    create_batch_from_csv_file = append_csv_string

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

    def stream_rows(self, ds, values):
        """Send a data row (or list of rows) to the given dataset's stream.

        The rows are added to the Dataset's stream resource. This does
        *not* immediately append the rows to the Dataset; to do that,
        call append_pending_stream periodically.

        If the 'values' argument is a dict, it is treated as one row of
        {variable_id: data value} pairs. The given data values must be
        in the Crunch I/O format (for example, category ids instead
        of names or numeric_values). Otherwise, the 'values' argument
        must be an iterable of such dicts.
        """
        if isinstance(values, dict):
            values = [values]
        return ds.session.post(
            ds.fragments.stream,
            data="\n".join([json.dumps(row, indent=None) for row in values])
        )


importer = Importer()
"""A default Importer."""
