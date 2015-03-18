# -*- coding: utf-8 -*-

from pycrunch import csvlib

class TestCSV:
	def test_unicode_values(self):
		"CSV rendering should handle simple unicode"
		rows = [[u'☃']]
		csvlib.rows_as_csv_file(rows)
