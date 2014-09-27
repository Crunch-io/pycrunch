from cStringIO import StringIO
import mimetypes
import os
import time

from pycrunch import shoji


class Importer(object):

    def __init__(self, async=True, retries=40, frequency=0.25):
        self.async = async
        self.retries = retries
        self.frequency = frequency

    def wait_for_batch_status(self, batch, status):
        """Wait for the given status and return the batch. Error if not reached."""
        for trial in range(self.retries):
            new_batch = batch.session.get(batch.self).payload
            st = new_batch.body['status']
            if st in ('error', 'failed'):
                raise ValueError("The batch was not fully appended.")
            elif st == 'conflict':
                raise ValueError("The batch had conflicts.")
            elif st == status:
                return new_batch
            else:
                time.sleep(self.frequency)
        else:
            raise ValueError("The batch did not reach the '%s' state in the "
                             "given time. Please check again later." % status)

    def append_csv_string(self, ds, csv_string, filename=None):
        """Append the given string of CSV data to the dataset. Return its Batch."""
        if filename is None:
            filename = 'upload.csv'
        source_url = self.add_source(ds, filename, StringIO(csv_string), "text/csv")
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

    def create_batch_from_source(self, ds, source_url):
        """Create and return a Batch on the given dataset for the given source."""
        # TODO: support async=False
        batch = shoji.Entity(ds.session, body={
            'source': source_url,
            'workflow': [],
            'async': True,
        })
        ds.batches.create(batch)

        # Wait for the batch to be ready...
        self.wait_for_batch_status(batch, 'ready')

        # Tell the batch to start appending.
        batch_part = shoji.Entity(batch.session, body={'status': 'importing'})
        batch.patch(data=batch_part.json)

        # Wait for the batch to be imported...
        return self.wait_for_batch_status(batch, 'imported')


importer = Importer()
"""A default Importer."""
