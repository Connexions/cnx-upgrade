# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

import sys
import psycopg2
from psycopg2.extras import DictCursor

from cnxarchive.to_html import _gen_xsl, DEFAULT_XMLPARSER
from io import BytesIO
from lxml import etree

__all__ = ('cli_loader',)

DEFAULT_ID_SELECT_QUERY = '''\
SELECT module_ident FROM modules
WHERE now() - revised < '1 day'::interval 
ORDER BY revised
'''

COUNT_LINKS_QUERY = '''
with urls as (select unnest(xpath('//c:link/@url',convert_from(file,'utf8')::xml, ARRAY[ARRAY['c', 'http://cnx.rice.edu/cnxml']]))::text as url 
       from latest_modules natural join module_files natural join files 
       where  filename = 'index.cnxml' and module_ident = %s)
select count(*) from urls where urls.url ~ '^http://cnx.org/content/'
'''

fixlinks = _gen_xsl('legacy_links.xsl')

def convert_module(cursor,module_ident):
    """process given module cnxml - convert legacy url hard links to local, host-relative links"""
    cursor.execute(COUNT_LINKS_QUERY,(module_ident,))
    legacy_links = cursor.fetchone()[0]
    if legacy_links:
        cursor.execute("""select fileid, file from module_files natural join files where module_ident = %s and 
                          filename = 'index.cnxml'""", (module_ident,))
        fileid, filebuf = cursor.fetchone()
        
        filebits = etree.parse(BytesIO(filebuf),DEFAULT_XMLPARSER)
        fixedbits = str(fixlinks(filebits))
        cursor.execute("""insert into files (file) values(%s) returning fileid""", (psycopg2.Binary(fixedbits),))
        newfileid = cursor.fetchone()[0]
        cursor.execute("""insert into module_files (module_ident,fileid,filename) values (%s,%s,'index.legacy.cnxml');
        delete from module_files where module_ident = %s and fileid = %s;
        insert into module_files (module_ident,fileid,filename) values (%s,%s,'index.cnxml')""",
                          (module_ident,fileid,module_ident,fileid,module_ident,newfileid))
        return legacy_links
    

def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic.
    """
    db_conn = kwargs['db_conn_str']
    id_select_query = kwargs['id_select_query']
    with psycopg2.connect(db_conn, cursor_factory=DictCursor) as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(id_select_query)
            docs = cursor.fetchall()
            if docs:
                sys.stderr.write('Number of documents: {}\n'.format(len(docs)))
                for i, doc in enumerate(docs):
                    module_ident = doc[0]
                    sys.stderr.write('Processing #{}, document ident {} -'.format(i, module_ident))
                    links = convert_module(cursor,module_ident)
                    sys.stderr.write(' {} links converted\n'.format(links))
                    if not(i % 100):
                        db_connection.commit()
                db_connection.commit()
                

def cli_loader(parser):
    """Used to load the CLI toggles and switches.
    """
    parser.add_argument('--id-select-query', default=DEFAULT_ID_SELECT_QUERY,
                        help='an SQL query that returns module_idents to '
                             'correct legacy links in'
                             'default {}'.format(DEFAULT_ID_SELECT_QUERY))
    return cli_command
