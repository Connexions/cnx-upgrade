# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades the schema form version 1 to version 2."""
import os
import psycopg2
from cnxarchive.database import DB_SCHEMA_FILES, _read_sql_file

__all__ = ('cli_loader', 'do_upgrade',)

here = os.path.abspath(os.path.dirname(__file__))

SQL_UPGRADE = """\
-- Drop the licenses flag that designate a license as
--   valid for contemporary publications.
ALTER TABLE licenses DROP "is_valid_for_publication";

-- Drop the collection sequence value for contemporary publications.
DROP SEQUENCE "collectionid_seq";

-- Add defaults to the modules table for moduleid and version.
ALTER TABLE modules ALTER COLUMN "moduleid" SET DEFAULT 'm' || nextval('"moduleid_seq"');
ALTER TABLE modules ALTER COLUMN "version" SET DEFAULT '1.1';
ALTER TABLE modules ALTER COLUMN "uuid" SET NOT NULL;
ALTER TABLE modules ALTER COLUMN "uuid" SET DEFAULT uuid_generate_v4();
-- Remove the the triggers.
DROP TRIGGER act_10_module_uuid_default ON modules;
DROP TRIGGER act_20_module_acl_upsert ON modules;
DROP TRIGGER module_moduleid_default ON modules;
DROP TRIGGER module_version_default ON modules;
DROP FUNCTION assign_moduleid_default ();
DROP FUNCTION assign_version_default ();
DROP FUNCTION assign_uuid_default ();
DROP FUNCTION upsert_document_acl ();


-- Drop the new tables for document_controls and document_acl.
DROP TABLE "document_acl";
DROP TYPE permission_type;
DROP TABLE "document_controls";


-- Drop the new column for files
ALTER TABLE files DROP COLUMN sha1;
DROP TRIGGER update_files_sha1 ON files;
DROP FUNCTION IF EXISTS update_sha1();
"""


def do_upgrade(db_connection):
    """Does the upgrade from version 1 to version 2."""
    with db_connection.cursor() as cursor:
        cursor.execute(SQL_UPGRADE)
    db_connection.commit()


def cli_command(**kwargs):
    """The command used by the CLI to invoke the upgrade logic."""
    connection_string = kwargs['db_conn_str']
    with psycopg2.connect(connection_string) as db_connection:
        do_upgrade(db_connection)


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    return cli_command
