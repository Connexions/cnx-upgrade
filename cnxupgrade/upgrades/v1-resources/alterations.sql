-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###



CREATE EXTENSION IF NOT EXISTS plpythonu;
-- This is named the same as the uuid function in Postgres,
--   but this one provides better comptibility across multiple platforms.
--   specifically uuid-ossp extension seems to often get broken in PostgresApp on OSX
CREATE OR REPLACE FUNCTION uuid_generate_v4 ()
RETURNS uuid LANGUAGE plpythonu
AS $$
import uuid; return uuid.uuid4()
$$ ;



-- Add the columns to the tables
ALTER TABLE modules ADD COLUMN "uuid" UUID;
ALTER TABLE latest_modules ADD COLUMN "uuid" UUID;
ALTER TABLE modules ALTER COLUMN version DROP DEFAULT;
ALTER TABLE modules ADD COLUMN "major_version" INTEGER DEFAULT 1;
ALTER TABLE modules ADD COLUMN "minor_version" INTEGER DEFAULT NULL;
ALTER TABLE latest_modules ADD COLUMN "major_version" INTEGER;
ALTER TABLE latest_modules ADD COLUMN "minor_version" INTEGER;
ALTER TABLE modules ADD COLUMN "google_analytics" TEXT;
ALTER TABLE latest_modules ADD COLUMN "google_analytics" TEXT;
ALTER TABLE modules ADD COLUMN "buylink" TEXT;
ALTER TABLE latest_modules ADD COLUMN "buylink" TEXT;



-- Update the modules with a default UUID.
ALTER TABLE modules DISABLE TRIGGER ALL;  -- disable update_latest_trigger


-- Update all modules to have a UUID value.
UPDATE modules SET uuid = data.uuid
FROM (
  SELECT uuid_generate_v4() as uuid, mid, idents
  FROM (
    SELECT moduleid AS mid, array_agg(module_ident) AS idents
    FROM modules GROUP BY moduleid
  ) AS grouped_modules
) AS data
WHERE
  moduleid = data.mid
  AND
  module_ident = any(data.idents)
;

-- Update the latest_modules with the new uuid values set on the related
--   modules table entries.

UPDATE latest_modules set uuid=m.uuid from modules m where latest_modules.module_ident = m.module_ident;

-- Update all modules to migrate the version value from version to
--   major_version and minor_version.
UPDATE modules
  SET major_version = split_part(version, '.', 1)::integer + split_part(version, '.', 2)::integer - 1;
UPDATE modules set minor_version = 1 where portal_type = 'Collection' AND minor_version IS NULL;
UPDATE latest_modules
  SET major_version = split_part(version, '.', 1)::integer + split_part(version, '.', 2)::integer - 1;
UPDATE latest_modules set minor_version = 1 where portal_type = 'Collection' AND minor_version IS NULL;

ALTER TABLE modules ENABLE TRIGGER ALL;



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
		authors, maintainers, licensors, parentauthors, google_analytics,
                major_version, minor_version)
  	VALUES (
         NEW.uuid, NEW.module_ident, NEW.portal_type, NEW.moduleid, NEW.version, NEW.name,
  	 NEW.created, NEW.revised, NEW.abstractid, NEW.stateid, NEW.doctype, NEW.licenseid,
  	 NEW.submitter, NEW.submitlog, NEW.parent, NEW.language,
	 NEW.authors, NEW.maintainers, NEW.licensors, NEW.parentauthors, NEW.google_analytics,
         NEW.major_version, NEW.minor_version );
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
	parentauthors=NEW.parentauthors,
	google_analytics=NEW.google_analytics,
        major_version=NEW.major_version,
        minor_version=NEW.minor_version
        WHERE module_ident=NEW.module_ident;
  END IF;

RETURN NEW;
END;

' LANGUAGE 'plpgsql';


-- Set constraints on the column ONLY after the data base been updated.
ALTER TABLE modules ALTER COLUMN "uuid" SET NOT NULL;
ALTER TABLE modules ALTER COLUMN "uuid" SET DEFAULT uuid_generate_v4();

-- store fulltext in the fti table

ALTER TABLE modulefti ADD COLUMN fulltext TEXT;

-- new hits tables
 
CREATE TABLE document_hits (
  documentid INTEGER NOT NULL,
  start_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  end_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  hits INTEGER DEFAULT 0,
  FOREIGN KEY (documentid) REFERENCES modules (module_ident) ON DELETE CASCADE
);

CREATE TABLE recent_hit_ranks (
  document UUID NOT NULL PRIMARY KEY,
  hits INTEGER DEFAULT 0,
  average FLOAT DEFAULT NULL,
  rank INTEGER DEFAULT NULL
);

CREATE TABLE overall_hit_ranks (
  document UUID NOT NULL PRIMARY KEY,
  hits INTEGER DEFAULT 0,
  average FLOAT DEFAULT NULL,
  rank INTEGER DEFAULT NULL
);

-- Create a view to map the legacy persons table to the new format

CREATE VIEW users AS
 SELECT persons.personid AS id, 
    persons.email, 
    persons.firstname, 
    persons.othername, 
    persons.surname, 
    persons.fullname, 
    persons.honorific AS title, 
    persons.lineage AS suffix, 
    persons.homepage AS website
   FROM persons;
