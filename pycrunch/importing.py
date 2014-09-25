import mimetypes
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

    def append_file(self, ds, f, filename=None, mimetype=None):
        """Append the given file-like object to the given dataset. Return its Batch."""
        if filename is None:
            filename = 'upload.crunch'

        if mimetype is None:
            mimetype, encoding = mimetypes.guess_type(filename)

        files = {'uploaded_file': (filename, f, mimetype)}
        sources_url = ds.user_url.catalogs['sources']
        # Don't call Catalog.post here; we want requests.Session to set
        # it with the multipart boundary param.
        source_url = ds.session.post(sources_url, files=files).headers["Location"]

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
