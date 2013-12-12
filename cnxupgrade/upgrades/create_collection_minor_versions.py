# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

import psycopg2

from cnxarchive.database import (get_collection_tree, next_version,
        republish_collection, rebuild_collection_tree, get_minor_version)

__all__ = ('cli_loader',)

DEFAULT_ID_SELECT_QUERY = '''\
SELECT module_ident FROM latest_modules
WHERE portal_type='Collection' AND minor_version=1
ORDER BY revised
'''

def create_collection_minor_versions(cursor, collection_ident):
    """Migration to create collection minor versions from the existing modules
    and collections """
    if get_minor_version(collection_ident, cursor) is None:
        # Not a collection so do nothing
        return

    # Get the collection tree
    # modules = []
    # Loop over each module
    #    If there is a version of the modules that have next_collection.revised > revised > collection.revised 
    #        modules.append((module_ident, revised))
    # sort modules by revised ascending
    # for each module in modules
    #    increment minor version of collection, with module's revised time
    #    rebuild collection tree

    # fetches the collection version of interest and the next version
    # and in case the collection version of interest is latest, revised for the
    # next version is now
    cursor.execute('''
    (
        WITH current AS (
            SELECT uuid, revised FROM modules WHERE module_ident = %s
        )
        SELECT m.module_ident, m.revised FROM modules m, current
        WHERE m.uuid = current.uuid AND m.revised >= current.revised
        ORDER BY m.revised
    )
    UNION ALL SELECT NULL, CURRENT_TIMESTAMP
    LIMIT 2;
    ''',
        [collection_ident])
    results = cursor.fetchall()
    this_module_ident, this_revised = results[0]
    next_module_ident, next_revised = results[1]

    # gather all relevant module versions
    sql = '''SELECT DISTINCT(m.module_ident), m.revised FROM modules m
    WHERE m.revised > %s AND m.revised < %s AND m.uuid = (
        SELECT uuid FROM modules WHERE module_ident = %s)
    ORDER BY m.revised
    '''

    old_module_idents = {}
    modules = []
    for module_ident, portal_type in get_collection_tree(collection_ident,
            cursor):
        if portal_type == 'Module':
            cursor.execute(sql, [this_revised, next_revised, module_ident])

            # get all the modules with the same uuid that have been published
            # between this collection version and the next version
            results = cursor.fetchall()

            # about what the loop below does...
            #
            # e.g. we have a module m1, and it was updated 3 times between the
            # time the collection is updated
            #
            # let's say the module_ident for current m1 is 1 and the updated
            # versions 3, 6, 9
            #
            # then results looks like [(3, revised), (6, revised), (9, revised)
            #
            # we need to know that 3 replaces 1, 6 replaces 3 and 9 replaces 6
            # so that we know what to change when we copy the collection tree
            #
            # so old_module_idents should have:
            # {3: 1, 6: 3, 9: 6}
            for i, data in enumerate(results):
                if i == 0:
                    old_module_idents[data[0]] = module_ident
                else:
                    old_module_idents[data[0]] = results[i - 1][0]
                modules.append(data)

    modules.sort(lambda a, b: cmp(a[1], b[1])) # sort modules by revised

    next_minor_version = next_version(collection_ident, cursor)
    for module_ident, module_revised in modules:
        new_ident = republish_collection(next_minor_version, collection_ident, cursor, revised=module_revised)
        rebuild_collection_tree(collection_ident, {
            collection_ident: new_ident,
            old_module_idents[module_ident]: module_ident,
            }, cursor)

        next_minor_version += 1
        collection_ident = new_ident

def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic.
    """
    db_conn = kwargs['db_conn_str']
    id_select_query = kwargs['id_select_query']
    with psycopg2.connect(db_conn) as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute("ALTER TABLE modules DISABLE TRIGGER module_published")

            cursor.execute(id_select_query)
            cols = cursor.fetchall()
            print 'Number of collections: {}'.format(len(cols))
            for i, col in enumerate(cols):
                module_ident = col[0]
                print 'Processing #{}, collection ident {}'.format(i, module_ident)
                create_collection_minor_versions(cursor, module_ident)
                if i % 10:
                    db_connection.commit()
            cursor.execute("ALTER TABLE modules ENABLE TRIGGER module_published")
        db_connection.commit()

def cli_loader(parser):
    """Used to load the CLI toggles and switches.
    """
    parser.add_argument('--id-select-query', default=DEFAULT_ID_SELECT_QUERY,
                        help='an SQL query that returns module_idents to '
                             'create collection minor versions for, '
                             'default {}'.format(DEFAULT_ID_SELECT_QUERY))
    return cli_command
