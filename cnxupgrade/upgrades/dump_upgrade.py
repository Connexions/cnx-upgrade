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

from cnxarchive.database import (get_collection_tree, next_version,
        republish_collection, rebuild_collection_tree, get_minor_version)

__all__ = ('cli_loader',)

DEFAULT_ID_SELECT_QUERY = '''\
SELECT module_ident FROM modules
WHERE now() - revised < '1 day'::interval 
ORDER BY revised
'''

def create_temp_load_tables(f):
        f.write('create temp table new_abstracts (abstractid int, abstract text);\n')
        f.write('create temp table new_keywords (keywordid int, word text);\n')
        f.write('create temp table new_files (fileid int, md5 text, file bytea);\n')
        f.write('''create temp table new_modules (
                        module_ident  int,
                        moduleid     text,
                        version       text,
                        name          text,
                        created       timestamptz,
                        revised       timestamptz,
                        abstractid    int,
                        licenseid     int,
                        doctype       text,
                        submitter     text,
                        submitlog     text,
                        stateid       int,
                        parent        int,
                        language      text,
                        authors       text[],
                        maintainers   text[],
                        licensors     text[],
                        parentauthors text[],
                        portal_type   text);\n''')
        f.write('create temp table new_module_files (module_ident int, fileid int, filename text,mimetype text);\n')
        f.write('create temp table new_modulefti (module_ident int, module_idx tsvector);\n')
        f.write('create temp table new_modulekeywords (module_ident int, keywordid int);\n')
        f.write('create temp table new_moduletags (module_ident int, tagid int);\n')

def copy_load_tables(f):
        f.write('insert into abstracts (abstractid,abstract) select * from new_abstracts;\n')
        f.write('insert into keywords (keywordid,word) select * from new_keywords;\n')
        f.write('insert into files (fileid,md5,file) select * from new_files;\n')
        f.write('''insert into modules (module_ident, moduleid, version, name, created, revised, abstractid,
                        licenseid, doctype, submitter, submitlog, stateid, parent, language, authors,
                        maintainers, licensors, parentauthors, portal_type) select * from new_modules;\n''')
        f.write('insert into module_files (module_ident,fileid,filename,mimetype ) select * from new_module_files;\n')
        f.write('insert into modulefti (module_ident,module_idx ) select * from new_modulefti;\n')
        f.write('insert into modulekeywords (module_ident,keywordid ) select * from new_modulekeywords;\n')
        f.write('insert into moduletags (module_ident,tagid ) select * from new_moduletags;\n')

def dump_module(cursor,module_ident, f):
    """walks the tables dumping SQL commands to transfer given module_ident and all its
       required child tables"""
    cursor.execute('select abstractid from modules where module_ident = %s', (module_ident,))
    res = cursor.fetchone()
    # Abstract
    abid = res[0]
    cursor.execute('select 1 from modules where abstractid = %s and module_ident < %s', (abid, module_ident))
    res = cursor.fetchone()
    if not(res):
        f.write('copy new_abstracts from stdin;\n')
        cursor.copy_expert('copy (select abstractid,abstract from abstracts where abstractid = %s) to stdout' % abid, f)
        f.write('\.\n')
    # Keywords
    cursor.execute('select keywordid from modulekeywords where module_ident = %s', (module_ident,))
    keyids = [k[0] for k in cursor.fetchall()]
    cursor.execute('select keywordid from modulekeywords where module_ident < %s', (module_ident,))
    old_keyids = [k[0] for k in cursor.fetchall()]
    new_keyids = [k for k in keyids if k not in old_keyids]
    if new_keyids:
        f.write('copy new_keywords from stdin;\n')
        cursor.copy_expert('copy (select keywordid,word from keywords  where keywordid in (%s)) to stdout' % str(new_keyids)[1:-1], f)
        f.write('\.\n')
    # Files
    cursor.execute('select fileid from module_files where module_ident = %s', (module_ident,))
    fileids = [i[0] for i in cursor.fetchall()]
    cursor.execute('select fileid from module_files where module_ident < %s', (module_ident,))
    old_fileids = [i[0] for i in cursor.fetchall()]
    new_fileids = [i for i in fileids if i not in old_fileids]
    new_fileids = {}.fromkeys(new_fileids).keys()
    if new_fileids:
        f.write('copy new_files from stdin;\n')
        cursor.copy_expert('copy (select fileid,md5,file from files  where fileid in (%s)) to stdout' % str(new_fileids)[1:-1], f)
        f.write('\.\n')
    
    f.write('copy new_modules from stdin;\n')
    cursor.copy_expert('''copy (select module_ident, moduleid, version, name, created, revised, abstractid,
                        licenseid, doctype, submitter, submitlog, stateid, parent, language, authors,
                        maintainers, licensors, parentauthors, portal_type from modules  where module_ident = %s) to stdout''' % module_ident, f)
    f.write('\.\n')
    f.write('copy new_module_files from stdin;\n')
    cursor.copy_expert('copy (select module_ident,fileid,filename,mimetype from module_files  where module_ident = %s) to stdout' % module_ident, f)
    f.write('\.\n')
    f.write('copy new_modulefti from stdin;\n')
    cursor.copy_expert('copy (select module_ident,module_idx from modulefti  where module_ident = %s) to stdout' % module_ident, f)
    f.write('\.\n')
    f.write('copy new_modulekeywords from stdin;\n')
    cursor.copy_expert('copy (select module_ident,keywordid from modulekeywords  where module_ident = %s) to stdout' % module_ident, f)
    f.write('\.\n')
    f.write('copy new_moduletags from stdin;\n')
    cursor.copy_expert('copy (select module_ident,tagid from moduletags  where module_ident = %s) to stdout' % module_ident, f)
    f.write('\.\n')
    
def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic.
    """
    db_conn = kwargs['db_conn_str']
    id_select_query = kwargs['id_select_query']
    filename = kwargs['filename']
    if filename:
        f = open(filename,'w')
    else:
        f = sys.stdout
    with psycopg2.connect(db_conn, cursor_factory=DictCursor) as db_connection:
        with db_connection.cursor() as cursor:
            cursor.execute(id_select_query)
            docs = cursor.fetchall()
            if docs:
                create_temp_load_tables(f)
                sys.stderr.write('Number of documents: {}\n'.format(len(docs)))
                for i, doc in enumerate(docs):
                    module_ident = doc[0]
                    sys.stderr.write('Processing #{}, document ident {}\n'.format(i, module_ident))
                    dump_module(cursor,module_ident,f)
                copy_load_tables(f)
                

def cli_loader(parser):
    """Used to load the CLI toggles and switches.
    """
    parser.add_argument('--id-select-query', default=DEFAULT_ID_SELECT_QUERY,
                        help='an SQL query that returns module_idents to '
                             'create sql transfer dumps for'
                             'default {}'.format(DEFAULT_ID_SELECT_QUERY))
    parser.add_argument('--filename', default=None,
                        help='filename to store sql dump, default stdio')
    return cli_command
