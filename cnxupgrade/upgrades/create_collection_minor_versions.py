# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

import datetime

import psycopg2

from cnxarchive.database import (get_collection_tree, next_version,
        republish_collection, rebuild_collection_tree, get_minor_version)

__all__ = ('cli_loader',)

DEFAULT_ID_SELECT_QUERY = '''\
SELECT module_ident FROM latest_modules
WHERE portal_type='Collection' AND minor_version=1
ORDER BY revised
'''

def fix_document_id_map(document_id_map):
    # Sometimes we end up with a document_id_map that looks like this:
    # {1: 5, 2: 3, 3: 4}
    # Which means document 1 is replaced by document 5,
    # document 2 by 3 and document 3 by 4
    #
    # But really we just want document 2 to be replaced by 4 directly
    # so we need to turn it into {1: 5, 2: 4}
    # so we know we're replacing document 2 with document 4, not 3
    for old_ident, new_ident in document_id_map.iteritems():
        if new_ident in document_id_map:
            document_id_map[old_ident] = document_id_map.pop(new_ident)
            break
    else:
        # went through the loop and nothing needs to be changed
        return
    fix_document_id_map(document_id_map)

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
            SELECT uuid, revised, minor_version FROM modules WHERE module_ident = %s
        )
        SELECT m.module_ident, m.revised, m.minor_version FROM modules m, current
        WHERE m.uuid = current.uuid AND m.revised >= current.revised
        ORDER BY m.revised
    )
    UNION ALL SELECT NULL, CURRENT_TIMESTAMP, 1
    LIMIT 2;
    ''',
        [collection_ident])
    results = cursor.fetchall()
    this_module_ident, this_revised, this_minor_version = results[0]
    next_module_ident, next_revised, next_minor_version = results[1]

    if next_minor_version != 1:
        # minor versions already created for this collection
        # so nothing to do
        return

    # gather all relevant module versions
    sql = '''SELECT DISTINCT(m.module_ident), m.revised FROM modules m
    WHERE m.revised > %s AND m.revised < %s AND
        m.uuid = (SELECT uuid FROM modules WHERE module_ident = %s) AND
        m.revised > (SELECT revised FROM modules WHERE module_ident = %s)
    ORDER BY m.revised
    '''

    old_module_idents = {}
    modules = []
    for module_ident, portal_type in get_collection_tree(collection_ident,
            cursor):
        if portal_type == 'Module':
            cursor.execute(sql, [this_revised, next_revised, module_ident, module_ident])

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

    # batch process modules that are revised within 24 hours of each other
    batched_modules = []
    last_revised = None
    for module_ident, module_revised in modules:
        if (last_revised is None or
                module_revised - last_revised >= datetime.timedelta(1)):
            batched_modules.append([(module_ident, module_revised)])
            last_revised = module_revised
        else:
            batched_modules[-1].append((module_ident, module_revised))

    next_minor_version = next_version(collection_ident, cursor)
    for modules in batched_modules:
        # revised should be the revised of the latest module
        module_revised = modules[-1][1]
        new_ident = republish_collection(next_minor_version, collection_ident,
                                         cursor, revised=module_revised)

        document_id_map = {collection_ident: new_ident}
        module_idents = [m[0] for m in modules]
        for module_ident, module_revised in modules:
            document_id_map[old_module_idents[module_ident]] = module_ident
        fix_document_id_map(document_id_map)

        rebuild_collection_tree(collection_ident, document_id_map, cursor)

        next_minor_version += 1
        collection_ident = new_ident

def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic.
    """
    db_conn = kwargs['db_conn_str']
    id_select_query = kwargs['id_select_query']
    with psycopg2.connect(db_conn) as db_connection:
        with db_connection.cursor() as cursor:

            cursor.execute(id_select_query)
            cols = cursor.fetchall()
            print 'Number of collections: {}'.format(len(cols))
            for i, col in enumerate(cols):
                module_ident = col[0]
                print 'Processing #{}, collection ident {}'.format(i, module_ident)
                create_collection_minor_versions(cursor, module_ident)
                if i % 10:
                    db_connection.commit()
        db_connection.commit()

def cli_loader(parser):
    """Used to load the CLI toggles and switches.
    """
    parser.add_argument('--id-select-query', default=DEFAULT_ID_SELECT_QUERY,
                        help='an SQL query that returns module_idents to '
                             'create collection minor versions for, '
                             'default {}'.format(DEFAULT_ID_SELECT_QUERY))
    return cli_command
