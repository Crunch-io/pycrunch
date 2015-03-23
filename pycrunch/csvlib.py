import csv
import six


def rows_as_csv_file(rows):
    """Return rows (iterable of lists of cells) as an open CSV file.

    Any cells in the given
    rows which contain None will be emitted as an empty cell in the CSV
    (nothing between the commas), which Crunch interprets as {"?": -1},
    the "No Data" system missing value.
    """
    # Write to a BytesIO because it joins encoded lines as we go
    # and a .read() of it (like requests.post will do) does not make a copy.
    out = six.BytesIO()

    sentinel = "__CSV_SENTINEL_NONE__"

    class EphemeralWriter():
        def write(self, line):
            line = line.replace('"' + sentinel + '"', "")
            out.write(line.encode('utf-8'))
    pipe = EphemeralWriter()

    writer = csv.writer(pipe, quoting=csv.QUOTE_NONNUMERIC, lineterminator='\n')
    for row in rows:
        writer.writerow([sentinel if cell is None else cell for cell in row])

    out.seek(0)

    return out
