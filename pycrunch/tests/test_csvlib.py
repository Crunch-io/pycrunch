# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import io
import csv
from unittest import TestCase

import six

from pycrunch import csvlib


class TestCSV(TestCase):

    def test_unicode_values(self):
        # CSV rendering should handle simple unicode
        rows = [['☃']]
        csvlib.rows_as_csv_file(rows)

    def test_result_is_binary(self):
        # Result should be a stream with a binary type
        res = csvlib.rows_as_csv_file([['foo']])
        assert isinstance(next(res), six.binary_type)

    def test_stdlib_unicode(self):
        # Demonstrate how one might go about writing unicode to a CSV
        # on Python 2 and Python 3.

        # See http://python3porting.com/problems.html#csv-api-changes
        # for more details.
        out = io.StringIO() if six.PY3 else io.BytesIO()
        w = csv.writer(out)
        row = ['☃']
        row = [
            cell.encode('utf-8')
                if six.PY2 and isinstance(cell, six.text_type)
                else cell
            for cell in row
        ]
        w.writerow(row)
