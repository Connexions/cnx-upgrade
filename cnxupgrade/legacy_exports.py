# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Command-line script to take collection ids as arguments,
get the export files from the legacy system and rename them
to something that cnx-archive understands
"""

import argparse
import os.path
import sys
import urllib2

import psycopg2

from .cli import DEFAULT_PSYCOPG_CONNECTION_STRING

DOWNLOAD_URL = 'http://cnx.org/content/{id}/{version}/{type}'

FILENAME = '{uuid}@{version}.{ext}'

GET_UUID_BY_ID_SQL = '''
SELECT m.uuid
FROM modules m
WHERE m.moduleid = %s
'''


GET_VERSIONS_BY_ID_SQL = '''
WITH versions AS (SELECT version AS legacy, 
         CONCAT_WS('.',major_version,minor_version) as version, 
         revised, 
         RANK() OVER (PARTITION BY version ORDER BY revised DESC) as rank
         FROM modules WHERE moduleid = %s) 
SELECT legacy, version FROM versions WHERE rank=1 ORDER BY revised DESC 
'''
GET_LATEST_VERSION_BY_ID_SQL = GET_VERSIONS_BY_ID_SQL  + ' LIMIT 1'


def get_export_file(moduleid, version, type, filename):
    """Get the export file from the legacy system and store it as filename
    """
    url = DOWNLOAD_URL.format(id=moduleid, version=version, type=type)
    chunksize = 8192
    try:
        content = urllib2.urlopen(url)
    except urllib2.HTTPError:
        sys.stderr.write('Unable to get "{}" from legacy system\n'.format(url))
        return
    print 'Downloading from "{}", saving as "{}"'.format(url, filename)
    with open(filename, 'wb') as out_file:
        while True:
            piece = content.read(chunksize)
            if not piece:
                break # finish copying file
            out_file.write(piece)

def get_export_filename(uuid, version, extension):
    """Return a filename for the legacy export file that cnx-archive
    understands
    """
    return FILENAME.format(uuid=uuid, version=version, ext=extension)

def get_export_types():
    """Return a list of export file types available for download
    """
    return [
            {'ext': 'pdf', 'type': 'pdf'},
            {'ext': 'epub', 'type': 'epub'},
            {'ext': 'xml', 'type': 'source'},
            {'ext': 'zip', 'type': 'offline'},
           ]

def get_uuid(cursor, collection_id):
    """Return the uuid for a legacy id
    """
    cursor.execute(GET_UUID_BY_ID_SQL, [collection_id])
    try:
        return cursor.fetchone()[0]
    except (IndexError, TypeError):
        sys.stderr.write('Unable to find collection "{}" in the database\n'
                         .format(collection_id))

def get_versions(cursor, collection_id, latest_only):
    """Return a list of versions that we have for a collection id
    """
    if latest_only:
        cursor.execute(GET_LATEST_VERSION_BY_ID_SQL, [collection_id])
    else:
        cursor.execute(GET_VERSIONS_BY_ID_SQL, [collection_id])
    for result in cursor.fetchall():
        yield result

def main(argv=None):
    parser = argparse.ArgumentParser(description='Get export files from legacy '
            'systems and rename them to something that cnx-archive understands')
    parser.add_argument('--db-conn-str',
                        default=DEFAULT_PSYCOPG_CONNECTION_STRING,
                        help='a psycopg2 db connection string')
    parser.add_argument('--dest', metavar='destination_directory',
                        default='/var/www/files/',
                        help='the directory where all the downloads should go')
    parser.add_argument('--latest-only', dest='latest_only',
                        action='store_true', default=True,
                        help='download only the latest version')
    parser.add_argument('--all-versions', dest='latest_only',
                        action='store_false', default=False,
                        help='download all versions')
    parser.add_argument('collection_ids', metavar='collection_id', nargs='+',
                        help='Collection id, e.g. col12345')
    args = parser.parse_args(argv)

    with psycopg2.connect(args.db_conn_str) as db_connection:
        with db_connection.cursor() as cursor:
            for collection_id in args.collection_ids:

                print 'Processing collection "{}"'.format(collection_id)
                uuid = get_uuid(cursor, collection_id)
                if uuid is None:
                    # skip if a collection id is not in the db
                    continue

                for legacy, version in get_versions(cursor, collection_id,
                                            args.latest_only):
                    for export_type in get_export_types():
                        extension = export_type['ext']
                        type = export_type['type']
                        filename = get_export_filename(uuid, version, extension)
                        get_export_file(collection_id, legacy, type,
                                        os.path.join(args.dest, filename))


if __name__ == '__main__':
    main()
