# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

import glob
from io import BytesIO
import os.path
import shutil
import sys
import tempfile
import unittest
import urllib2

from . import (
        DB_CONNECTION_STRING,
        postgresql_fixture, db_connect,
        )


class LegacyExportsTestCase(unittest.TestCase):
    """Tests for cnx-upgrade-legacy-exports script
    """
    fixture = postgresql_fixture

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()

        # set up test data
        cursor.execute('''
ALTER TABLE modules DISABLE TRIGGER ALL;
INSERT INTO abstracts VALUES (1, 'sample abstracts');
INSERT INTO modules VALUES (1, 'Collection', 'col11406', 'e79ffde3-7fb4-4af3-9ec8-df648b391597', '1.7', 'College Physics', '2013-07-31 14:07:20.342798-05', '2013-08-31 14:07:20.342798-05', 1, 11, '', '', '', NULL, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8, 1df3bab1-1dc7-4017-9b3a-960a87e706b1}', '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, 'UA-XXXXX-Y', NULL, 7, 1);
INSERT INTO modules VALUES (2, 'Collection', 'col11406', 'e79ffde3-7fb4-4af3-9ec8-df648b391597', '1.6', 'College Physics', '2013-07-31 14:07:20.342798-05', '2013-07-31 14:07:20.342798-05', 1, 11, '', '', '', NULL, NULL, 'en', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8}', '{e5a07af6-09b9-4b74-aa7a-b7510bee90b8, 1df3bab1-1dc7-4017-9b3a-960a87e706b1}', '{9366c786-e3c8-4960-83d4-aec1269ac5e5}', NULL, 'UA-XXXXX-Y', NULL, 6, 1);
        ''')

        # Mock response from legacy site
        self.responses = ['']
        self.response_id = -1
        def urlopen(url):
            self.response_id += 1
            return BytesIO(self.responses[self.response_id])

        # Patch urllib2.urlopen to return the mock responses
        original_urlopen = urllib2.urlopen
        urllib2.urlopen = urlopen
        self.addCleanup(setattr, urllib2, 'urlopen', original_urlopen)

        # Capture stderr
        original_stderr = sys.stderr
        sys.stderr = BytesIO()
        self.addCleanup(setattr, sys, 'stderr', original_stderr)

        # Capture stdout
        original_stdout = sys.stdout
        sys.stdout = BytesIO()
        self.addCleanup(setattr, sys, 'stdout', original_stdout)

        # Create a temporary directory for the test downloads
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)

        # Default args for the script
        self.argv = ['--db-conn-str', DB_CONNECTION_STRING,
                     '--dest', self.tmpdir]

    def tearDown(self):
        self.fixture.tearDown()

    def call_target(self):
        from ..legacy_exports import main
        return main(self.argv)

    def test_file_not_found(self):
        def urlopen(url):
            self.response_id += 1
            if self.response_id == 0:
                raise urllib2.HTTPError(url, 404, 'Not Found', None, None)
            return BytesIO('asdf')
        urllib2.urlopen = urlopen
        self.argv += ['col11406']
        self.call_target()
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        self.assertEqual(sys.stdout.getvalue(),
                'Processing collection "col11406"\n'
                'Downloading from "http://cnx.org/content/col11406/1.7/epub", '
                'saving as "{}/{}@7.1.epub"\n'
                'Downloading from "http://cnx.org/content/col11406/1.7/source", '
                'saving as "{}/{}@7.1.xml"\n'
                'Downloading from "http://cnx.org/content/col11406/1.7/offline", '
                'saving as "{}/{}@7.1.zip"\n'
                .format(self.tmpdir, uuid, self.tmpdir, uuid, self.tmpdir, uuid))
        self.assertEqual(sys.stderr.getvalue(),
                'Unable to get "http://cnx.org/content/col11406/1.7/pdf" from legacy system\n')

    def test_collection_not_in_db(self):
        self.argv += ['col12345']
        self.call_target()
        self.assertEqual(sys.stderr.getvalue(),
                         'Unable to find collection "col12345" in the database\n')

    def test_all_versions(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'
        self.responses = ['col11406@1.7/pdf',
                          'col11406@1.7/epub',
                          'col11406@1.7/xml',
                          'col11406@1.7/zip',
                          'col11406@1.6/pdf',
                          'col11406@1.6/epub',
                          'col11406@1.6/xml',
                          'col11406@1.6/zip',
                         ]
        self.argv += ['--all-versions', 'col11406']
        self.call_target()
        self.assertEqual(sys.stdout.getvalue(),
                'Processing collection "col11406"\n'
                'Downloading from "http://cnx.org/content/col11406/1.7/pdf", '
                'saving as "{tmpdir}/{uuid}@7.1.pdf"\n'
                'Downloading from "http://cnx.org/content/col11406/1.7/epub", '
                'saving as "{tmpdir}/{uuid}@7.1.epub"\n'
                'Downloading from "http://cnx.org/content/col11406/1.7/source", '
                'saving as "{tmpdir}/{uuid}@7.1.xml"\n'
                'Downloading from "http://cnx.org/content/col11406/1.7/offline", '
                'saving as "{tmpdir}/{uuid}@7.1.zip"\n'
                'Downloading from "http://cnx.org/content/col11406/1.6/pdf", '
                'saving as "{tmpdir}/{uuid}@6.1.pdf"\n'
                'Downloading from "http://cnx.org/content/col11406/1.6/epub", '
                'saving as "{tmpdir}/{uuid}@6.1.epub"\n'
                'Downloading from "http://cnx.org/content/col11406/1.6/source", '
                'saving as "{tmpdir}/{uuid}@6.1.xml"\n'
                'Downloading from "http://cnx.org/content/col11406/1.6/offline", '
                'saving as "{tmpdir}/{uuid}@6.1.zip"\n'
                .format(uuid=uuid, tmpdir=self.tmpdir))

        # Check the files downloaded
        filenames = glob.glob(os.path.join(self.tmpdir, '*'))
        filenames = [os.path.basename(f) for f in filenames]
        filenames.sort()
        self.assertEqual(filenames,
                ['{}@6.1.epub'.format(uuid),
                 '{}@6.1.pdf'.format(uuid),
                 '{}@6.1.xml'.format(uuid),
                 '{}@6.1.zip'.format(uuid),
                 '{}@7.1.epub'.format(uuid),
                 '{}@7.1.pdf'.format(uuid),
                 '{}@7.1.xml'.format(uuid),
                 '{}@7.1.zip'.format(uuid)])

        # Check the content of the files downloaded
        expected_content = ['col11406@1.6/epub',
                            'col11406@1.6/pdf',
                            'col11406@1.6/xml',
                            'col11406@1.6/zip',
                            'col11406@1.7/epub',
                            'col11406@1.7/pdf',
                            'col11406@1.7/xml',
                            'col11406@1.7/zip']
        for i, filename in enumerate(filenames):
            with open(os.path.join(self.tmpdir, filename)) as f:
                self.assertEqual(f.read(), expected_content[i])

    def test_create_hardlink(self):
        uuid = 'e79ffde3-7fb4-4af3-9ec8-df648b391597'

        # Pretend we already have col11406-1.7.offline.zip and col11406-1.7.epub
        # the script should create a hard link instead of downloading the file
        with open(os.path.join(self.tmpdir, 'col11406-1.7.offline.zip'),
                  'w') as f:
            f.write('col11406-1.7.offline.zip')
        with open(os.path.join(self.tmpdir, 'col11406-1.7.epub'), 'w') as f:
            f.write('col11406-1.7.epub')
        # We already have the collection.xml with the new naming system
        # the script should leave that alone
        with open(os.path.join(self.tmpdir, '{}@7.1.xml'.format(uuid)),
                  'w') as f:
            f.write('col11406-1.7.xml')

        # Mock response for the pdf file
        self.responses = ['col11406-1.7.pdf']

        self.argv += ['col11406']
        self.call_target()

        # Make sure we have the right files in tmpdir
        filenames = glob.glob(os.path.join(self.tmpdir, '*'))
        filenames = [os.path.basename(f) for f in filenames]
        filenames.sort()
        self.assertEqual(filenames,
                ['col11406-1.7.epub',
                 'col11406-1.7.offline.zip',
                 '{}@7.1.epub'.format(uuid),
                 '{}@7.1.pdf'.format(uuid),
                 '{}@7.1.xml'.format(uuid),
                 '{}@7.1.zip'.format(uuid)])

        # Check the content of the files
        expected_content = ['col11406-1.7.epub',
                            'col11406-1.7.offline.zip',
                            'col11406-1.7.epub',
                            'col11406-1.7.pdf',
                            'col11406-1.7.xml',
                            'col11406-1.7.offline.zip']
        for i, filename in enumerate(filenames):
            with open(os.path.join(self.tmpdir, filename)) as f:
                self.assertEqual(f.read(), expected_content[i])
