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
-- Update the licenses with a flag that to designate a license as
--   valid for contemporary publications.
ALTER TABLE licenses ADD "is_valid_for_publication" BOOLEAN DEFAULT FALSE;
UPDATE licenses SET is_valid_for_publication = 't' WHERE licenseid = 12;


-- Create the collection sequence value for contemporary publications.
CREATE SEQUENCE "collectionid_seq" start 10000 increment 1 maxvalue 2147483647 minvalue 1 cache 1;
-- Set the collection sequence based on the highest known value.
SELECT setval('collectionid_seq', max(substr(moduleid, 4)::int))
FROM modules
WHERE portal_type = 'Collection';


-- Adjust the modules table to remove the default from moduleid and version.
--   This is done to make way for the triggers that assign a default moduleid
--   or update the sequence value based on the value recieved from a legacy
--   publication. The version default is removed to signify when a publication
--   is legacy vs contemporary. All legacy publications will insert with a
--   value for version, while contemporary publications will not.
-- Drop the moduleid default from the modules table.
ALTER TABLE modules ALTER COLUMN "moduleid" DROP DEFAULT;
ALTER TABLE modules ALTER COLUMN "version" DROP DEFAULT;
ALTER TABLE modules ALTER COLUMN "uuid" DROP NOT NULL;
ALTER TABLE modules ALTER COLUMN "uuid" DROP DEFAULT;
-- Put the triggers in place.
CREATE OR REPLACE FUNCTION assign_moduleid_default ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import assign_moduleid_default_trigger
  return assign_moduleid_default_trigger(plpy, TD)
$$ LANGUAGE plpythonu;
CREATE OR REPLACE FUNCTION assign_version_default ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import assign_version_default_trigger
  return assign_version_default_trigger(plpy, TD)
$$ LANGUAGE plpythonu;
CREATE OR REPLACE FUNCTION assign_uuid_default ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import assign_uuid_default_trigger
  return assign_uuid_default_trigger(plpy, TD)
$$ LANGUAGE plpythonu;
CREATE OR REPLACE FUNCTION upsert_document_acl ()
  RETURNS TRIGGER
AS $$
  from cnxarchive.database import upsert_document_acl_trigger
  return upsert_document_acl_trigger(plpy, TD)
$$ LANGUAGE plpythonu;
CREATE TRIGGER act_10_module_uuid_default
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE assign_uuid_default();
CREATE TRIGGER act_20_module_acl_upsert
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE upsert_document_acl();
CREATE TRIGGER module_moduleid_default
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE assign_moduleid_default();
CREATE TRIGGER module_version_default
  BEFORE INSERT ON modules FOR EACH ROW
  EXECUTE PROCEDURE assign_version_default();


-- Add in the new tables for document_controls and document_acl.
CREATE TABLE "document_controls" (
  -- An association table that is a controlled set of UUID identifiers
  -- for document/module input. This prevents collisions between existing documents,
  -- and publication pending documents, while still providing the publishing system
  -- a means of assigning an identifier where the documents will eventually live.
  "uuid" UUID PRIMARY KEY DEFAULT uuid_generate_v4()
);
CREATE TYPE permission_type AS ENUM (
  'publish'
);
CREATE TABLE "document_acl" (
  "uuid" UUID,
  "user_id" TEXT,
  "permission" permission_type NOT NULL,
  PRIMARY KEY ("uuid", "user_id", "permission"),
  FOREIGN KEY ("uuid") REFERENCES document_controls ("uuid")
);


-- Populate the new tables from the modules table.
INSERT INTO document_controls (uuid) select uuid from modules group by uuid;
INSERT INTO document_acl (uuid, user_id, permission)
  SELECT uuid, unnest(authors), 'publish'::permission_type FROM modules
  UNION
  SELECT uuid, unnest(maintainers), 'publish'::permission_type FROM modules;
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
