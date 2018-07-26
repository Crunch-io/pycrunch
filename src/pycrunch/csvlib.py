"""
CSV support for Crunch.

The two functions, rows_as_csv_file* should be kept in sync.
The differing behavior cannot be factored out due to
the underlying stdlib csv module implementation and
performance characteristics of Python function calls.
"""

from __future__ import unicode_literals

import io
import csv
import six


def rows_as_csv_file(rows):
    """Return rows (iterable of lists of cells) as a CSV file open
    in binary mode.

    Any cells in the given
    rows which contain None will be emitted as an empty cell in the CSV
    (nothing between the commas), which Crunch interprets as {"?": -1},
    the "No Data" system missing value.
    """
    # Write to a StringIO because it joins lines as we go
    # and a .read() of it (like requests.post will do) does not make a copy.
    out = io.StringIO() if six.PY3 else io.BytesIO()

    sentinel = "__CSV_SENTINEL_NONE__"

    class EphemeralWriter():
        def write(self, line):
            line = line.replace(str('"' + sentinel + '"'), str())
            out.write(line)
    pipe = EphemeralWriter()

    writer = csv.writer(pipe, quoting=csv.QUOTE_NONNUMERIC, lineterminator='\n')
    for row in rows:
        row = [sentinel if cell is None else cell for cell in row]
        row = [
            cell.encode('utf-8')
            if six.PY2 and isinstance(cell, six.text_type) else cell
            for cell in row
        ]
        writer.writerow(row)

    out.seek(0)

    if six.PY3:
        out = io.BytesIO(out.getvalue().encode('utf-8'))

    return out


def rows_as_csv_file_clean(rows):
    """Return rows (iterable of lists of cells) as a CSV file open
    in binary mode.

    Duplicate of rows_as_csv_file except
    None values are emitted
    normally by the Python csv library, which means as (quoted) empty strings.
    Use this function if the rows contain no None values or
    if None values are only used for "text" types and the empty
    string is a suitable representation for those values.
    """
    # Write to a StringIO because it joins lines as we go
    # and a .read() of it (like requests.post will do) does not make a copy.
    out = io.StringIO() if six.PY3 else io.BytesIO()

    writer = csv.writer(out, quoting=csv.QUOTE_NONNUMERIC, lineterminator='\n')
    for row in rows:
        row = [
            cell.encode('utf-8')
            if six.PY2 and isinstance(cell, six.text_type) else cell
            for cell in row
        ]
        writer.writerow(row)

    out.seek(0)

    if six.PY3:
        out = io.BytesIO(out.getvalue().encode('utf-8'))

    return out
