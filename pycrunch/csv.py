from __future__ import absolute_import

import re
import csv

import six


class CSVLineGenerator:
    r"""
    Apply csv writer .write operations to individual rows.

    >>> gen = CSVLineGenerator()

    >>> rows = [
    ...     ('id', 'val', 'val2'),
    ...     (1, 2),
    ...     (2, -1, None),
    ...     (3, None, "foo"),
    ...     (4, "", "bar"),
    ... ]
    >>> out = gen.process(rows)
    >>> next(out)
    '"id","val","val2"\n'
    >>> next(out)
    '1,2\n'

    None values are rendered as empty strings

    >>> next(out)
    '2,-1,""\n'
    >>> next(out)
    '3,"","foo"\n'
    """
    def __init__(self, **writer_args):
        writer_args.setdefault('quoting', csv.QUOTE_NONNUMERIC)
        writer_args.setdefault('lineterminator', '\n')
        self.writer = csv.writer(self, **writer_args)

    def as_csv(self, row):
        self.writer.writerow(row)
        return vars(self).pop('last_write')

    def write(self, line):
        self.last_write = line

    def process(self, rows):
        return six.moves.map(self.as_csv, rows)


class NoneAsEmptyLineGenerator(CSVLineGenerator):
    r"""
    Support for preventing None values from being rendered as
    empty strings.

    >>> gen = CrunchLineGenerator()

    >>> rows = [
    ...     ('id', 'val', 'val2'),
    ...     (1, 2),
    ...     (2, -1, None),
    ...     (3, None, "foo"),
    ...     (4, "", "bar"),
    ... ]
    >>> out = gen.process(rows)
    >>> next(out)
    '"id","val","val2"\n'
    >>> next(out)
    '1,2\n'

    None values are rendered as null cells

    >>> next(out)
    '2,-1,\n'
    >>> next(out)
    '3,,"foo"\n'

    Empty strings are still rendered as empty strings

    >>> next(out)
    '4,"","bar"\n'
    """

    sentinel = "CSV_SENTINEL_NONE"

    def as_csv(self, row):
        row = list(six.moves.map(self._inject_sentinel, row))
        line = super(NoneAsEmptyLineGenerator, self).as_csv(row)
        return self.remove_sentinel(line)

    def _inject_sentinel(self, cell):
        if cell is None:
            return self.sentinel
        return cell

    def remove_sentinel(self, row):
        pattern = '"' + re.escape(self.sentinel) + '"'
        return re.sub(pattern, "", row)
