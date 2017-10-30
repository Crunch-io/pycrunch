# -*- coding: utf-8 -*-

from __future__ import unicode_literals

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

    def test_rows_as_csv_file(self):
        # None should be emitted as an empty cell (unquoted)
        rows = [[0, 1, None, "bananas"]]
        fp = csvlib.rows_as_csv_file(rows)
        self.assertEqual(fp.read(), b'0,1,,"bananas"\n')

    def test_rows_as_csv_file_clean(self):
        # None should be emitted as an empty string (quoted)
        rows = [[0, 1, None, "bananas"]]
        fp = csvlib.rows_as_csv_file_clean(rows)
        self.assertEqual(fp.read(), b'0,1,"","bananas"\n')
