Testing data
============


:legacy-data.sql: Contains a data set extracted from a legacy database
    structure that was populated using cnx-populate. This
    data is a SQL dump using::

        pg_dump --data-only -T licenses -T tags -T trees \
          --inserts --disable-triggers \
          -d $DB_NAME > legacy-data.sql
