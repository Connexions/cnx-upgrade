cnx-upgrade
===========
This is a limited-use repository/module that contains code to migrate an
existing legacy Connexions/Rhaptos database/instance to be dual-use capable of
supporting both its existing legacy app, and an instance of cnx-archive (The
Connexions-rewrite archival storage app). It is intended to provide a framework
to enable this migration, and future migrations as new components are completed
and rolled out to replace legacy functionality.

There are potentially two different kinds of upgrade steps supported by this
package: ones that mutate data only (e.g. convert one form of stored file to
another) and ones that change the underlying database schema. Either class of
upgrade should be prepared to be run multiple times against the same target:
i.e. they should be idempotent and (potentially) restartable. Whether a
particular step implements this by overwriting all previous work, or commits
incremental results depends on the needs of that particular step.

Upgrade steps that create new functionality by creating new database objects
should strive to import the commands to create those objects from cnx-archive
(DRY principle). A typical schema migration step would likely have 3 phases::

   1. mutate existing database objects  (ALTER TABLE type commands)
        this step could include data dependent steps, in order to make
        sure that the schema is complete and self consistent. I.e. if a
        not-null column is added, filling it with appropriate values.
   2. create new data base objects (import SQL from cnx-archive)
        these might be either tables or functions or both.
   3. upgrade/fill new objects to match existing data.
        depending on the magnitude of this step, it might need to be broken out
        as a separately callable upgrade step.

Upgrade steps that alter data should not change schema, but only fill in new
data objects (created in an earlier schema upgrade step), or extend existing
data (add additional formats of stored files, new values for lookup tables
(e.g. subjects or possible licenses) etc. If the step is particularly complex,
provide a means to run it in stages: at minimum, report progress.

Note that the top-level cnx-upgrade command defers to individual upgrade steps
for commandline processing, so additional step specific parameters can be added.

[![Build Status](https://travis-ci.org/Connexions/cnx-upgrade.svg?branch=master)](https://travis-ci.org/Connexions/cnx-upgrade)
