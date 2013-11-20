# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

"""Tests for cnx-upgrades cnxml7
"""

import os
import unittest

import lxml.etree

from . import TESTING_DATA_DIRECTORY

def get_data_file(filename):
    path = os.path.join(TESTING_DATA_DIRECTORY, filename)
    with open(path) as f:
        return f.read()

class TransformsTestCase(unittest.TestCase):
    """Tests for cnxupgrade.upgrades.cnxml7.transforms
    """

    def call_target(self, source, version=None):
        from ..upgrades.cnxml7 import transforms
        return transforms.upgrade_document(source, version=version)

    def test_successful(self):
        cnxml = get_data_file('m10470-2.2.cnxml')
        new_cnxml, result, message = self.call_target(cnxml, version='0.5')
        self.assertEqual(message, '')
        self.assertTrue(result)
        self.assertTrue('cnxml-version="0.7"' in new_cnxml)
        # Assert generated cnxml is valid xml
        self.assertTrue(lxml.etree.fromstring(new_cnxml) is not None)

    def test_missing_namespace_declaration(self):
        cnxml = get_data_file('m12563-1.6.cnxml')
        new_cnxml, result, message = self.call_target(cnxml, version='0.5')
        self.assertEqual(message, '')
        self.assertTrue(result)
        self.assertTrue('cnxml-version="0.7"' in new_cnxml)
        # Assert generated cnxml is valid xml
        self.assertTrue(lxml.etree.fromstring(new_cnxml) is not None)
