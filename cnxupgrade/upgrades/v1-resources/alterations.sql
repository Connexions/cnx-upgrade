-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###



CREATE EXTENSION IF NOT EXISTS plpythonu;
-- This is named the same as the uuid function in Postgres,
--   but this one provides better comptibility accross multiple platforms.
CREATE OR REPLACE FUNCTION uuid_generate_v4 ()
RETURNS uuid LANGUAGE plpythonu
AS $$
import uuid; return uuid.uuid4()
$$ ;



-- Add the columns to the tables
ALTER TABLE modules ADD COLUMN "uuid" UUID;
ALTER TABLE latest_modules ADD COLUMN "uuid" UUID;
ALTER TABLE modules ADD COLUMN "major_version" INTEGER DEFAULT 1;
ALTER TABLE modules ADD COLUMN "minor_version" INTEGER DEFAULT 1;
ALTER TABLE latest_modules ADD COLUMN "major_version" INTEGER DEFAULT 1;
ALTER TABLE latest_modules ADD COLUMN "minor_version" INTEGER DEFAULT 1;



-- Update the modules with a default UUID.
ALTER TABLE modules DISABLE TRIGGER ALL;  -- disable update_latest_trigger

CREATE AGGREGATE array_accum (anyelement) (
  -- Used to build an array of module_idents for creating a joint UUID.
  sfunc = array_append,
  stype = anyarray,
  initcond = '{}'
);

-- Update all modules to have a UUID value.
UPDATE modules SET uuid = data.uuid
FROM (
  SELECT uuid_generate_v4() as uuid, mid, idents
  FROM (
    SELECT moduleid AS mid, array_accum(module_ident) AS idents
    FROM modules GROUP BY moduleid
  ) AS grouped_modules
) AS data
WHERE
  moduleid = data.mid
  AND
  module_ident = any(data.idents)
;

DROP AGGREGATE array_accum (anyelement);

ALTER TABLE modules ENABLE TRIGGER ALL;

-- Update all modules to migrate the version value from version to
--   major_version and minor_version.
UPDATE modules
  SET major_version = split_part(version, '.', 1)::integer,
      minor_version = split_part(version, '.', 2)::integer
;



-- Shoe in a new version of the update_latest_trigger
--   to be UUID column aware.
CREATE OR REPLACE FUNCTION update_latest() RETURNS trigger AS '
BEGIN
  IF TG_OP = ''INSERT'' THEN
      DELETE FROM latest_modules WHERE moduleid = NEW.moduleid;
      INSERT into latest_modules (
                uuid, module_ident, portal_type, moduleid, version, name,
  		created, revised, abstractid, stateid, doctype, licenseid,
  		submitter,submitlog, parent, language,
		authors, maintainers, licensors, parentauthors)
  	VALUES (
         NEW.uuid, NEW.module_ident, NEW.portal_type, NEW.moduleid, NEW.version, NEW.name,
  	 NEW.created, NEW.revised, NEW.abstractid, NEW.stateid, NEW.doctype, NEW.licenseid,
  	 NEW.submitter, NEW.submitlog, NEW.parent, NEW.language,
	 NEW.authors, NEW.maintainers, NEW.licensors, NEW.parentauthors
         );
  END IF;

  IF TG_OP = ''UPDATE'' THEN
      UPDATE latest_modules SET
        uuid=NEW.uuid,
        moduleid=NEW.moduleid,
        portal_type=NEW.portal_type,
        version=NEW.version,
        name=NEW.name,
        created=NEW.created,
        revised=NEW.revised,
        abstractid=NEW.abstractid,
        stateid=NEW.stateid,
        doctype=NEW.doctype,
        licenseid=NEW.licenseid,
	submitter=NEW.submitter,
	submitlog=NEW.submitlog,
        parent=NEW.parent,
	language=NEW.language,
	authors=NEW.authors,
	maintainers=NEW.maintainers,
	licensors=NEW.licensors,
	parentauthors=NEW.parentauthors
        WHERE module_ident=NEW.module_ident;
  END IF;

RETURN NEW;
END;

' LANGUAGE 'plpgsql';



-- Update the latest_modules with the new uuid values set on the related
--   modules table entries.
UPDATE latest_modules SET uuid = mmm.uuid
FROM (
  SELECT uuid, module_ident AS mid
  FROM modules
) AS mmm
WHERE
  module_ident = mmm.mid
;

-- Set constraints on the column ONLY after the data base been updated.
ALTER TABLE modules ALTER COLUMN "uuid" SET NOT NULL;
ALTER TABLE modules ALTER COLUMN "uuid" SET DEFAULT uuid_generate_v4();
ALTER TABLE latest_modules ALTER COLUMN "uuid" SET NOT NULL;
