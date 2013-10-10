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
ALTER TABLE modules ADD COLUMN "minor_version" INTEGER DEFAULT NULL;
ALTER TABLE latest_modules ADD COLUMN "major_version" INTEGER DEFAULT 1;
ALTER TABLE latest_modules ADD COLUMN "minor_version" INTEGER DEFAULT 1;
ALTER TABLE modules ADD COLUMN "google_analytics" TEXT;
ALTER TABLE latest_modules ADD COLUMN "google_analytics" TEXT;
ALTER TABLE modules ADD COLUMN "buylink" TEXT;
ALTER TABLE latest_modules ADD COLUMN "buylink" TEXT;



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

-- No longer needed.
DROP AGGREGATE array_accum (anyelement);

-- Update all modules to migrate the version value from version to
--   major_version and minor_version.
UPDATE modules
  SET major_version = split_part(version, '.', 1)::integer,
      minor_version = split_part(version, '.', 2)::integer
;
UPDATE latest_modules
  SET major_version = split_part(version, '.', 1)::integer,
      minor_version = split_part(version, '.', 2)::integer
;

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



-- Trees table contains structure of a collection, with pointers into the documents table
CREATE SEQUENCE nodeid_seq
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;

CREATE TABLE trees (
  nodeid INTEGER DEFAULT nextval('nodeid_seq'::regclass) NOT NULL,
  parent_id INTEGER,
  documentid INTEGER, -- foreign key documents (documentid),
  title TEXT, -- override title
  childorder INTEGER, -- position within parent node
  latest BOOLEAN, -- is this node supposed to track upstream changes
  PRIMARY KEY (nodeid),
  FOREIGN KEY (parent_id) REFERENCES trees (nodeid) ON DELETE CASCADE
);

-- the unique index insures only one top-level tree per document metadata
CREATE UNIQUE INDEX trees_unique_doc_idx on trees(documentid) where parent_id is null;



-- Trigger function to shred collection.xml documents into the trees records.
CREATE OR REPLACE FUNCTION shred_collxml (doc TEXT) RETURNS VOID
as $$

from xml import sax

# While the collxml files we process potentially contain many of these
# namespaces, I take advantage of the fact that almost none of the
# localnames (tags names) acutally overlap. The one case that does (title)
# actually works in our favor, since we want to treat it the same anyway.

ns = { "cnx":"http://cnx.rice.edu/cnxml",
       "cnxorg":"http://cnx.rice.edu/system-info",
       "md":"http://cnx.rice.edu/mdml",
       "col":"http://cnx.rice.edu/collxml",
       "cnxml":"http://cnx.rice.edu/cnxml",
       "m":"http://www.w3.org/1998/Math/MathML",
       "q":"http://cnx.rice.edu/qml/1.0",
       "xhtml":"http://www.w3.org/1999/xhtml",
       "bib":"http://bibtexml.sf.net/",
       "cc":"http://web.resource.org/cc/",
       "rdf":"http://www.w3.org/1999/02/22-rdf-syntax-ns#"
}

NODE_INS=plpy.prepare("INSERT INTO trees (parent_id,documentid,childorder) SELECT $1, module_ident, $2 from modules where moduleid = $3 and version = $4 returning nodeid", ("int","int","text","text"))
NODE_NODOC_INS=plpy.prepare("INSERT INTO trees (parent_id,childorder) VALUES ($1, $2) returning nodeid", ("int","int"))
NODE_TITLE_UPD=plpy.prepare("UPDATE trees set title = $1 from modules where nodeid = $2 and (documentid is null or (documentid = module_ident and name != $1))", ("text","int"))

def _do_insert(pid,cid,oid=0,ver=0):
    if oid:
        res = plpy.execute(NODE_INS,(pid,cid,oid,ver))
        if res.nrows() == 0: # no documentid found
            plpy.execute(NODE_NODOC_INS,(pid,cid))
    else:
        res = plpy.execute(NODE_NODOC_INS,(pid,cid))
    if res.nrows():
        nodeid=res[0]["nodeid"]
    else:
        nodeid = None
    return nodeid

def _do_update(title,nid):
    plpy.execute(NODE_TITLE_UPD, (title,nid))

class ModuleHandler(sax.ContentHandler):
    def __init__(self):
        self.parents = [None]
        self.childorder = 0
        self.map = {}
        self.tag = u''
        self.contentid = u''
        self.version = u''
        self.title = u''
        self.nodeid = 0
        self.derivedfrom = [None]

    def startElementNS(self, (uri, localname), qname, attrs):
        self.map[localname] = u''
        self.tag = localname

        if localname == 'module':
            self.childorder[-1] += 1
            nodeid = _do_insert(self.parents[-1],self.childorder[-1],attrs[(None,"document")],attrs[(ns["cnxorg"],"version-at-this-collection-version")])
            if nodeid:
                self.nodeid = nodeid

        elif localname == 'subcollection':
            # TODO insert a metadata record into modules table for subcol.
            self.childorder[-1] += 1
            nodeid = _do_insert(self.parents[-1],self.childorder[-1])
            if nodeid:
                self.nodeid = nodeid
                self.parents.append(self.nodeid)
            self.childorder.append(1)

        elif localname == 'derived-from':
            self.derivedfrom.append(True)


    def characters(self,content):
        self.map[self.tag] += content

    def endElementNS(self, (uris, localname), qname):
        if localname == 'content-id' and not self.derivedfrom[-1]:
            self.contentid = self.map[localname]
        elif localname == 'version' and not self.derivedfrom[-1]:
            self.version = self.map[localname]
        elif localname == 'title' and not self.derivedfrom[-1]:
            self.title = self.map[localname]
            if self.parents[-1]: # current node is a subcollection or module
               _do_update(self.title.encode('utf-8'), self.nodeid)

        elif localname == 'derived-from':
            self.derivedfrom.pop()

        elif localname == 'metadata':
            # We know that at end of metadata, we have got the collection info
            self.childorder = [0]
            nodeid = _do_insert(None,self.childorder[-1], self.contentid, self.version)
            if nodeid:
                self.nodeid = nodeid
                self.parents.append(self.nodeid)
            self.childorder.append(1)

        elif localname == 'content':
            #this occurs at the end of each container class: collection or sub.
            self.parents.pop()
            self.childorder.pop()


parser = sax.make_parser()
parser.setFeature(sax.handler.feature_namespaces, 1)
parser.setContentHandler(ModuleHandler())

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
parser.parse(StringIO(doc))
$$
language plpythonu;

create or replace function shred_collxml (fid int)  returns void as
$$
select shred_collxml(convert_from(file,'UTF8')) from files where fileid = fid
$$
language sql;

create or replace function shred_collxml_trigger () returns trigger as $$
BEGIN
PERFORM shred_collxml(NEW.fileid);
RETURN NEW;
END;
$$
LANGUAGE plpgsql;

drop trigger if exists shred_collxml on module_files;

CREATE TRIGGER shred_collxml
  BEFORE INSERT ON module_files
  FOR EACH row WHEN (NEW.filename = 'collection.xml')
    EXECUTE PROCEDURE shred_collxml_trigger ()
;



-- Populate the trees table from the latest_modules by utilizing
--   the shred_collxml trigger.
WITH latest_idents AS
  (SELECT module_ident AS ident FROM latest_modules)
SELECT shred_collxml(fileid) FROM module_files
  WHERE filename = 'collection.xml'
        AND module_ident IN (SELECT ident FROM latest_idents)
;



-- Fuction to make a JSON object from a tree record
CREATE OR REPLACE FUNCTION tree_to_json(TEXT, TEXT) RETURNS TEXT as $$
select string_agg(toc,'
'
) from (
WITH RECURSIVE t(node, title, path,value, depth, corder) AS (
    SELECT nodeid, title, ARRAY[nodeid], documentid, 1, ARRAY[childorder]
    FROM trees tr, modules m
    WHERE m.uuid::text = $1 AND
          concat_ws('.',  m.major_version, m.minor_version) = $2 AND
      tr.documentid = m.module_ident
UNION ALL
    SELECT c1.nodeid, c1.title, t.path || ARRAY[c1.nodeid], c1.documentid, t.depth+1, t.corder || ARRAY[c1.childorder] /* Recursion */
    FROM trees c1 JOIN t ON (c1.parent_id = t.node)
    WHERE not nodeid = any (t.path)
)
SELECT
    REPEAT('    ', depth - 1) || '{"id":"' || COALESCE(m.uuid::text,'subcol') ||concat_ws('.', '@'||m.major_version, m.minor_version) ||'",' ||
      '"title":'||to_json(COALESCE(title,name))||
      CASE WHEN (depth < lead(depth,1,0) over(w)) THEN ', "contents":['
           WHEN (depth > lead(depth,1,0) over(w) AND lead(depth,1,0) over(w) = 0 ) THEN '}'||REPEAT(']}',depth - lead(depth,1,0) over(w) - 1)
           WHEN (depth > lead(depth,1,0) over(w) AND lead(depth,1,0) over(w) != 0 ) THEN '}'||REPEAT(']}',depth - lead(depth,1,0) over(w))||','
           ELSE '},' END
      AS "toc"
FROM t left join  modules m on t.value = m.module_ident
    WINDOW w as (ORDER BY corder) order by corder ) tree ;
$$ LANGUAGE SQL;
