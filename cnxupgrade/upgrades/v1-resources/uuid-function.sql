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
