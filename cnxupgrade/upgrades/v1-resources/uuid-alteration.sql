-- ###
-- Copyright (c) 2013, Rice University
-- This software is subject to the provisions of the GNU Affero General
-- Public License version 3 (AGPLv3).
-- See LICENCE.txt for details.
-- ###

alter table modules add column "uuid" UUID NOT NULL DEFAULT uuid_generate_v4();
alter table latest_modules add column "uuid" UUID NOT NULL;
