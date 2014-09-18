# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Migrate google analytics code from legacy site to cnx-archive
"""

import urllib2

import psycopg2

__all__ = ('cli_loader',)

SQL_GET_COLLECTIONS = """\
SELECT moduleid
FROM latest_modules
"""

SQL_INSERT_GOOGLE_ANALYTICS_CODE = """\
UPDATE modules
SET google_analytics = %(google_analytics)s
WHERE moduleid = %(moduleid)s
"""

DEFAULT_LEGACY_HOST = 'legacy.cnx.org'
LEGACY_GA_URL = 'http://{host}/content/{colid}/latest/getGoogleAnalyticsTrackingCode'

def get_ga_from_legacy(moduleid,host):
    return urllib2.urlopen(LEGACY_GA_URL.format(
        colid=moduleid, host=host)).read()

def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    host = kwargs['legacy_host']
    with psycopg2.connect(connection_string) as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(SQL_GET_COLLECTIONS)
            for (moduleid,) in cursor.fetchall():
                ga_code = get_ga_from_legacy(moduleid, host)
                print moduleid
                if ga_code:
                    cursor.execute(SQL_INSERT_GOOGLE_ANALYTICS_CODE, {
                        'google_analytics': ga_code,
                        'moduleid': moduleid,
                        })

def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    parser.add_argument('--legacy-host', default=DEFAULT_LEGACY_HOST,
                        help="where to fetch legacy GA codes from default {host}".format(host=DEFAULT_LEGACY_HOST))
    return cli_command
