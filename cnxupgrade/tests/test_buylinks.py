# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

from io import StringIO
import unittest
import urllib2

from .test_upgrades_to_html import (
    DB_CONNECTION_STRING,
    postgresql_fixture, db_connect,
    )


class GetBuylinksTestCase(unittest.TestCase):
    """Tests for the get_buylinks script
    """
    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()

        # set up test data
        cursor.execute('''
ALTER TABLE modules DISABLE TRIGGER ALL;
INSERT INTO modules VALUES (1, 'Collection', 'col11406', 'e79ffde3-7fb4-4af3-9ec8-df648b391597', '1.7', 'College Physics', '2013-07-31 14:07:20.342798-05', '2013-07-31 14:07:20.342798-05', 1, 11, '', '', '', NULL, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8, 1df3bab1-1dc7-4017-9b3a-960a87e706b1}', '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, 'UA-XXXXX-Y', NULL, 1, 7);
INSERT INTO modules VALUES (2, 'Module', 'm42955', '209deb1f-1a46-4369-9e0d-18674cf58a3e', '1.7', 'Preface to College Physics', '2013-07-31 14:07:20.542211-05', '2013-07-31 14:07:20.542211-05', NULL, 11, '', '', '', NULL, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8, 1df3bab1-1dc7-4017-9b3a-960a87e706b1}', '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, NULL, NULL, 7, NULL);
        ''')

        # Mock commandline arguments for ..scripts.get_buylinks.main
        self.argv = ['--db-conn-str', DB_CONNECTION_STRING]

        # Mock response from plone site:
        # responses should be assigned to self.responses by individual tests
        self.responses = ['']
        self.response_id = -1
        def urlopen(url):
            self.response_id += 1
            return StringIO(unicode(self.responses[self.response_id]))
        original_urlopen = urllib2.urlopen
        urllib2.urlopen = urlopen
        self.addCleanup(setattr, urllib2, 'urlopen', original_urlopen)

    def tearDown(self):
        self.fixture.tearDown()

    def call_target(self):
        from ..buylinks import main
        return main(self.argv)

    @db_connect
    def get_buylink_from_db(self, cursor, collection_id):
        cursor.execute(
                'SELECT m.buylink FROM modules m WHERE m.moduleid = %(moduleid)s;',
                {'moduleid': collection_id})
        return cursor.fetchone()[0]

    def test(self):
        self.argv.append('col11406')
        self.argv.append('m42955')
        self.responses = [
                # response for col11406
                "[('title', ''), "
                "('buyLink', 'http://buy-col11406.com/download')]",
                # response for m42955
                "[('title', ''), "
                "('buyLink', 'http://buy-m42955.com/')]"]
        self.call_target()

        self.assertEqual(self.get_buylink_from_db('col11406'),
                'http://buy-col11406.com/download')
        self.assertEqual(self.get_buylink_from_db('m42955'),
                'http://buy-m42955.com/')

    def test_no_buylink(self):
        self.argv.append('m42955')
        self.responses = ["('title', '')"]
        self.call_target()

        self.assertEqual(self.get_buylink_from_db('m42955'), None)

    def test_not_a_buylink(self):
        self.argv.append('m42955')
        self.responses = [
                "[('title', ''), "
                "('old_buyLink', 'http://buy-col11406.com/download')]",]
        self.call_target()

        self.assertEqual(self.get_buylink_from_db('m42955'), None)

    def test_collection_not_in_db(self):
        self.argv.append('col11522')
        self.responses = ("[('title', ''), "
                "('buyLink', 'http://buy-col11522.com/download')]",)
        # Just assert that the script does not fail
        self.call_target()
