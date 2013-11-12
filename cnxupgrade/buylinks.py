# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Command-line script to take collection ids as arguments, get the buy link
for each collection from the plone site and insert into the database.
"""
import sys
import re
import argparse
import urllib2

import psycopg2

from .cli import DEFAULT_PSYCOPG_CONNECTION_STRING


PROPERTY_URL = 'http://cnx.org/content/{}/latest/propertyItems'

UPDATE_BUYLINK = '''
UPDATE modules
SET buylink = %(buylink)s
WHERE moduleid = %(moduleid)s ;
'''


def get_buylink(url):
    content = urllib2.urlopen(url).read()
    buylink = re.search("'buyLink', '([^']*)'", content)
    if buylink:
        return buylink.group(1)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Insert the buy links'
            ' of collections from the plone site into the database')
    parser.add_argument('--db-conn-str',
                        default=DEFAULT_PSYCOPG_CONNECTION_STRING,
                        help="a psycopg2 db connection string")
    parser.add_argument('collection_ids', metavar='collection_id', nargs='+',
            help='Collection id, e.g. col11522')
    args = parser.parse_args(argv)

    with psycopg2.connect(args.db_conn_str) as db_connection:
        with db_connection.cursor() as cursor:
            for collection_id in args.collection_ids:
                buylink = get_buylink(PROPERTY_URL.format(collection_id))
                if not buylink:
                    continue
                args = {'moduleid': collection_id, 'buylink': buylink}
                cursor.execute(UPDATE_BUYLINK, args)


if __name__ == '__main__':
    main()
