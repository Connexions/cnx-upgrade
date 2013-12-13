# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

from io import BytesIO
import os
import sys
import unittest
import uuid

from . import postgresql_fixture, db_connect, DB_CONNECTION_STRING


class FixDocumentIdMapTestCase(unittest.TestCase):
    def call_target(self, document_id_map):
        from ..upgrades.create_collection_minor_versions import fix_document_id_map
        return fix_document_id_map(document_id_map)

    def test_no_change(self):
        m = {1: 10, 2: 5, 3: 7}
        self.call_target(m)
        self.assertEqual(m, {1: 10, 2: 5, 3: 7})

    def test_success(self):
        m = {1: 5, 2: 3, 3: 4}
        self.call_target(m)
        self.assertEqual(m, {1: 5, 2: 4})


class CollectionMigrationTestCase(unittest.TestCase):
    """Tests for creating collection minor versions for collections that are
    already in the database
    """
    fixture = postgresql_fixture

    @classmethod
    def setUpClass(cls):
        os.environ['PGTZ'] = 'America/Whitehorse'

    @classmethod
    def tearDownClass(cls):
        del os.environ['PGTZ']

    @db_connect
    def setUp(self, cursor):
        self.fixture.setUp()
        cursor.execute('ALTER TABLE modules DISABLE TRIGGER module_published')
        cursor.execute('''INSERT INTO abstracts VALUES (1,
            'abstract') ''')

    def tearDown(self):
        self.fixture.tearDown()

    def call_target(self, *args, **kwargs):
        from ..upgrades.create_collection_minor_versions import create_collection_minor_versions
        return create_collection_minor_versions(*args, **kwargs)

    def insert_modules(self, cursor, modules):
        # modules should be a list of (portal_type, moduleid, uuid, version,
        # name, revised, major_version, minor_version)
        for m in modules:
            cursor.execute('''INSERT INTO modules VALUES (
            DEFAULT, %s, %s, %s, %s, %s, '2013-07-31 00:00:00.000000+02',
            %s, 1, 11, '', '', '', NULL, NULL, 'en', '{}', '{}', '{}', NULL,
            NULL, NULL, %s, %s) RETURNING module_ident''', m)
            yield cursor.fetchone()[0]

    def create_collection_tree(self, cursor, relationships):
        # relationships should look like this:
        # ((parent_module_ident, child_module_ident), ...)
        # parent_module_ident should be None for the root
        childorder = 0
        module_ident_to_nodeid = {}
        for parent_module_ident, child_module_ident in relationships:
            cursor.execute('''INSERT INTO trees VALUES (
            DEFAULT, %s, %s, '', %s, NULL) RETURNING nodeid''', [
                module_ident_to_nodeid.get(parent_module_ident, None),
                child_module_ident, childorder])
            childorder += 1
            module_ident_to_nodeid[child_module_ident] = cursor.fetchone()[0]

    @db_connect
    def test_not_a_collection(self, cursor):
        """Test case for when the object is not a collection
        """
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_num_modules = cursor.fetchone()[0]

        module_idents = list(self.insert_modules(cursor, (
            ('Collection', 'col1', str(uuid.uuid4()), '1.1', 'col1',
                '2013-12-12 19:11:00.000000+02', 1, 1),
            ('Module', 'm1', str(uuid.uuid4()), '1.1', 'm1',
                '2013-12-12 19:11:00.000000+02', 1, None),
            ('Collection', 'col2', str(uuid.uuid4()), '1.1', 'col2',
                '2013-12-12 19:11:00.000000+02', 1, 1,),
            )))

        self.create_collection_tree(cursor, (
            (None, module_idents[0]),
            (module_idents[0], module_idents[1]),
            ))
        self.create_collection_tree(cursor, (
            (None, module_idents[2]),
            (module_idents[2], module_idents[1]),
            ))

        self.call_target(cursor, module_idents[1])

        # Running create_collection_minor_versions on a module should not
        # create any extra modules
        cursor.execute('SELECT COUNT(*) FROM modules')
        self.assertEqual(cursor.fetchone()[0], old_num_modules + 3)

    @db_connect
    def test_minor_versions_already_created(self, cursor):
        """Test case for when minor versions already exist
        """
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_num_modules = cursor.fetchone()[0]

        m1_uuid = str(uuid.uuid4())
        m2_uuid = str(uuid.uuid4())
        c1_uuid = str(uuid.uuid4())
        module_idents = list(self.insert_modules(cursor, (
            # portal_type, moduleid, uuid, version, name, revised,
            # major_version, minor_version
            ('Module', 'm1', m1_uuid, '1.1', 'Name of module m1',
                '2013-10-01 11:24:00.000000+02', 1, None),
            ('Module', 'm2', m2_uuid, '1.9', 'Name of module m2',
                '2013-10-01 12:24:00.000000+02', 9, None),
            ('Collection', 'c1', c1_uuid, '1.5', 'Name of collection c1',
                '2013-10-02 21:43:00.000000+02', 5, 1),
            ('Module', 'm1', m1_uuid, '1.2', 'Name of module m1',
                '2013-10-02 22:24:00.000000+02', 2, None),
            ('Module', 'm1', m1_uuid, '1.3', 'Name of module m1',
                '2013-10-02 23:24:00.000000+02', 3, None),
            ('Collection', 'c1', c1_uuid, '1.5', 'Name of collection c1',
                '2013-10-02 23:24:00.000000+02', 5, 2),
            ('Collection', 'c1', c1_uuid, '1.6', 'Name of collection c1',
                '2013-10-03 12:00:00.000000+02', 6, 1),
            )))

        self.create_collection_tree(cursor, (
            (None, module_idents[2]),
            (module_idents[2], module_idents[0]),
            (module_idents[2], module_idents[1])))

        self.create_collection_tree(cursor, (
            (None, module_idents[5]),
            (module_idents[5], module_idents[4]),
            (module_idents[5], module_idents[1])))

        self.create_collection_tree(cursor, (
            (None, module_idents[6]),
            (module_idents[6], module_idents[4]),
            (module_idents[6], module_idents[1])))

        self.call_target(cursor, module_idents[2])
        self.call_target(cursor, module_idents[5])
        self.call_target(cursor, module_idents[6])

        # Assert that the script did not add any additional collections
        cursor.execute('SELECT COUNT(*) FROM modules')
        new_num_modules = cursor.fetchone()[0]
        self.assertEqual(old_num_modules + len(module_idents), new_num_modules)

    @db_connect
    def test_no_minor_version(self, cursor):
        """Test case for when it is not necessary to create a minor version for
        a collection
        """
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_num_modules = cursor.fetchone()[0]

        m1_uuid = str(uuid.uuid4())
        m2_uuid = str(uuid.uuid4())
        c1_uuid = str(uuid.uuid4())
        module_idents = list(self.insert_modules(cursor, (
            # portal_type, moduleid, uuid, version, name, revised,
            # major_version, minor_version
            ('Module', 'm1', m1_uuid, '1.1', 'Name of module m1',
                '2013-10-01 11:24:00.000000+02', 1, None),
            ('Module', 'm2', m2_uuid, '1.9', 'Name of module m2',
                '2013-10-01 12:24:00.000000+02', 9, None),
            ('Collection', 'c1', c1_uuid, '1.5', 'Name of collection c1',
                '2013-10-02 21:43:00.000000+02', 5, 1),
            ('Collection', 'c1', c1_uuid, '1.6', 'Name of collection c1',
                '2013-10-03 12:00:00.000000+02', 6, 1),
            )))

        self.create_collection_tree(cursor, (
            (None, module_idents[2]),
            (module_idents[2], module_idents[0]),
            (module_idents[2], module_idents[1])))

        self.create_collection_tree(cursor, (
            (None, module_idents[3]),
            (module_idents[3], module_idents[0]),
            (module_idents[3], module_idents[1])))

        self.call_target(cursor, module_idents[2])
        self.call_target(cursor, module_idents[3])

        cursor.execute('SELECT COUNT(*) FROM modules')
        new_num_modules = cursor.fetchone()[0]
        self.assertEqual(old_num_modules + 4, new_num_modules)

    @db_connect
    def test_create_minor_versions(self, cursor):
        """Test case for when there are modules published in between collection
        versions and there is a need to create minor versions of a collection
        """
        cursor.execute('SELECT COUNT(*) FROM modules')
        old_num_modules = cursor.fetchone()[0]

        m1_uuid = str(uuid.uuid4())
        m2_uuid = str(uuid.uuid4())
        m3_uuid = str(uuid.uuid4())
        c1_uuid = str(uuid.uuid4())
        module_idents = list(self.insert_modules(cursor, (
            # portal_type, moduleid, uuid, version, name, revised,
            # major_version, minor_version
            ('Module', 'm1', m1_uuid, '1.1', 'Name of module m1',
                '2013-10-01 11:24:00.000000-07', 1, None),
            ('Module', 'm2', m2_uuid, '1.9', 'Name of module m2',
                '2013-10-01 12:24:00.000000-07', 9, None),
            ('Module', 'm3', m3_uuid, '1.1', 'Name of module m3',
                '2013-10-01 13:24:00.000000-07', 1, None),

            ('Collection', 'c1', c1_uuid, '1.5', 'Name of collection c1',
                '2013-10-02 21:43:00.000000-07', 5, 1),

            ('Module', 'm1', m1_uuid, '1.2', 'Changed name of module m1',
                '2013-10-03 09:00:00.000000-07', 2, None),

            ('Collection', 'c1', c1_uuid, '1.6', 'Name of collection c1',
                '2013-10-03 12:00:00.000000-07', 6, 1),

            ('Module', 'm1', m1_uuid, '1.3', 'Changed name again m1',
                '2013-10-03 12:01:00.000000-07', 3, None),
            # Modules published within 24 hours
            ('Module', 'm2', m2_uuid, '1.10', 'Changed name of module m2',
                '2013-10-05 12:02:00.000000-07', 10, None),
            ('Module', 'm2', m2_uuid, '1.11', 'Changed name of module m2',
                '2013-10-05 18:03:00.000000-07', 11, None),
            ('Module', 'm3', m3_uuid, '1.2', 'm3',
                '2013-10-05 23:05:00.000000-07', 2, None),

            ('Module', 'm3', m3_uuid, '1.3', 'm3',
                '2013-10-06 12:05:00.000000-07', 3, None),

            ('Collection', 'c1', c1_uuid, '1.7', 'Name of collection c1',
                '2013-10-07 12:00:00.000000-07', 7, 1),
            )))

        self.create_collection_tree(cursor, (
            (None, module_idents[3]),
            (module_idents[3], module_idents[0]),
            (module_idents[3], module_idents[1]),
            (module_idents[3], module_idents[2])))

        self.create_collection_tree(cursor, (
            (None, module_idents[5]),
            (module_idents[5], module_idents[4]),
            (module_idents[5], module_idents[1]),
            (module_idents[5], module_idents[2])))

        self.create_collection_tree(cursor, (
            (None, module_idents[11]),
            (module_idents[11], module_idents[6]),
            (module_idents[11], module_idents[8]),
            (module_idents[11], module_idents[10])))

        cursor.execute('SELECT COUNT(*) FROM modules')
        new_num_modules = cursor.fetchone()[0]
        # we inserted 12 rows into the modules table
        self.assertEqual(old_num_modules + 12, new_num_modules)

        self.call_target(cursor, module_idents[3])
        self.call_target(cursor, module_idents[5])

        old_num_modules = new_num_modules
        cursor.execute('SELECT COUNT(*) FROM modules')
        new_num_modules = cursor.fetchone()[0]
        # we should have inserted 4 minor versions for c1: 5.2, 6.2, 6.3, 6.4
        self.assertEqual(old_num_modules + 4, new_num_modules)

        tree_sql = '''
        WITH RECURSIVE t(node, parent, document, title, childorder, latest, path) AS (
            SELECT tr.*, ARRAY[tr.nodeid] FROM trees tr
            WHERE tr.documentid = %s
        UNION ALL
            SELECT c.*, path || ARRAY[c.nodeid]
            FROM trees c JOIN t ON c.parent_id = t.node
            WHERE not c.nodeid = ANY(t.path)
        )
        SELECT * FROM t'''

        # Check c1 v5.2
        cursor.execute('''SELECT * FROM modules
        WHERE uuid = %s AND major_version = %s AND minor_version = %s
        ''', [c1_uuid, 5, 2])
        rev_5_2 = cursor.fetchone()
        # revised
        self.assertEqual(str(rev_5_2[7]), '2013-10-03 09:00:00-07:00')

        # Check tree contains m1 v1.2 and m2 v1.9 and m3 v1.1
        cursor.execute(tree_sql, [rev_5_2[0]])
        tree = cursor.fetchall()
        self.assertEqual(len(tree), 4)
        self.assertEqual(tree[0][2], rev_5_2[0])
        self.assertEqual(tree[1][2], module_idents[4])
        self.assertEqual(tree[2][2], module_idents[1])
        self.assertEqual(tree[3][2], module_idents[2])

        # Check c1 v6.2
        cursor.execute('''SELECT * FROM modules
        WHERE uuid = %s AND major_version = %s AND minor_version = %s
        ''', [c1_uuid, 6, 2])
        rev_6_2 = cursor.fetchone()
        self.assertEqual(rev_6_2[4], '1.6') # legacy version
        # revised
        self.assertEqual(str(rev_6_2[7]), '2013-10-03 12:01:00-07:00')

        # Check tree contains m1 v1.3 and m2 v1.9 and m3 v1.1
        cursor.execute(tree_sql, [rev_6_2[0]])
        tree = cursor.fetchall()
        self.assertEqual(len(tree), 4)
        self.assertEqual(tree[0][2], rev_6_2[0])
        self.assertEqual(tree[1][2], module_idents[6])
        self.assertEqual(tree[2][2], module_idents[1])
        self.assertEqual(tree[3][2], module_idents[2])

        # Check c1 v6.3
        cursor.execute('''SELECT * FROM modules
        WHERE uuid = %s AND major_version = %s AND minor_version = %s
        ''', [c1_uuid, 6, 3])
        rev_6_3 = cursor.fetchone()
        self.assertEqual(rev_6_3[4], '1.6') # legacy version
        # revised
        self.assertEqual(str(rev_6_3[7]), '2013-10-05 23:05:00-07:00')

        # Check tree contains m1 v1.3 and m2 v1.11 and m3 v1.2
        # m2 v1.10 v1.11 and m3 v1.2 increment the minor
        # version only once
        cursor.execute(tree_sql, [rev_6_3[0]])
        tree = cursor.fetchall()
        self.assertEqual(len(tree), 4)
        self.assertEqual(tree[0][2], rev_6_3[0])
        self.assertEqual(tree[1][2], module_idents[6])
        self.assertEqual(tree[2][2], module_idents[8])
        self.assertEqual(tree[3][2], module_idents[9])

        # Check c1 v6.4
        cursor.execute('''SELECT * FROM modules
        WHERE uuid = %s AND major_version = %s AND minor_version = %s
        ''', [c1_uuid, 6, 4])
        rev_6_4 = cursor.fetchone()
        self.assertEqual(rev_6_4[4], '1.6') # legacy version
        # revised
        self.assertEqual(str(rev_6_4[7]), '2013-10-06 12:05:00-07:00')

        # Check tree contains m1 v1.3 and m2 v1.11 and m3 v1.3
        cursor.execute(tree_sql, [rev_6_4[0]])
        tree = cursor.fetchall()
        self.assertEqual(len(tree), 4)
        self.assertEqual(tree[0][2], rev_6_4[0])
        self.assertEqual(tree[1][2], module_idents[6])
        self.assertEqual(tree[2][2], module_idents[8])
        self.assertEqual(tree[3][2], module_idents[10])


class CliTestCase(unittest.TestCase):
    """Tests for cli_command
    """
    fixture = postgresql_fixture

    def setUp(self):
        self.fixture.setUp()
        from ..upgrades import create_collection_minor_versions as m
        original = m.create_collection_minor_versions
        self.addCleanup(setattr, m,
                'create_collection_minor_versions', original)

        self.call_count = 0
        def mock(*args, **kwargs):
            self.call_count += 1
            self.args = args
            self.kwargs = kwargs
        m.create_collection_minor_versions = mock

        # Capture stdout
        stdout = sys.stdout
        self.addCleanup(setattr, sys, 'stdout', stdout)
        sys.stdout = BytesIO()

    def tearDown(self):
        self.fixture.tearDown()

    def call_target(self, **kwargs):
        from ..upgrades.create_collection_minor_versions import cli_command
        return cli_command(**kwargs)

    def test(self):
        self.call_target(db_conn_str=DB_CONNECTION_STRING,
                         id_select_query='select 2')
        self.assertEqual(self.call_count, 1)
        self.assertEqual(str(type(self.args[0])),
                "<type 'psycopg2._psycopg.cursor'>")
        self.assertEqual(self.args[1], 2)
        self.assertEqual(self.kwargs, {})
