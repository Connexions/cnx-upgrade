# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Removes the Test/Draft subject and any content that has this subject."""
import psycopg2


__all__ = ('cli_loader', 'remove_subject',)


SQL_FOR_TAG_N_DOCUMENT_REMOVAL = """\
WITH tag AS
     (SELECT tagid AS id FROM tags WHERE tag = %s LIMIT 1),
     document_ids AS
     (SELECT module_ident AS id FROM moduletags, tag WHERE tagid = tag.id),
     deleted_tags AS
     (DELETE FROM moduletags WHERE tagid = (SELECT id FROM tag)),
     deleted_files AS
     (DELETE FROM module_files
      WHERE module_ident IN (SELECT id FROM document_ids)),
     deleted_documents AS
     (DELETE FROM modules WHERE module_ident IN (SELECT id FROM document_ids)
      RETURNING module_ident)
SELECT module_ident from deleted_documents;
"""


def remove_subject(subject_name, db_connection):
    """Removes a subject and all associated content."""
    with db_connection.cursor() as cursor:
        # Deletion of a module from the modules table will propogate
        #   the deletion to the latest_modules table.
        cursor.execute(SQL_FOR_TAG_N_DOCUMENT_REMOVAL,
                       (subject_name,))
        deleted_documents = cursor.fetchall()
        cursor.execute("DELETE FROM tags WHERE tag = %s", (subject_name,))
    return [x[0] for x in deleted_documents]

def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    with psycopg2.connect(connection_string) as db_connection:
        documents_removed = remove_subject('Test/Draft', db_connection)
    print(documents_removed)
    return 0


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    return cli_command
