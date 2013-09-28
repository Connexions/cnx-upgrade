# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
A utility for inputting JSON formated/table normalized connexions data
into a `cnx-archive` database.

The reason
----------

This utility exists so that population logic
that inputs the records into the database
can use the native column names as mapping keys.
This simply means that the data has an easy
one-to-one mapping from record files to the database.

While working with similar data in the context of `cnx-archive`,
the tests became very fragile when working with a SQL dump
that occasionally needed updated because of missing data, schema changes,
or the occasional hiccup.
The SQL dump was some 30mb and contained binaries.
In SQL dump scenario, surgical updates to the binaries is almost impossible.
Therefore, we've opt'ed to use a JSON pickling format for Python objects.
This provides us with human readable
and selectively automated data representations.

As an added benefit,
we can keep the data representations schema version specific.
This is helpful when making tests for new versions of the schema.
We can copy the previous version's data, modify it,
and build our tests in a similar fashion to those before it.

I (pumazi) also believe this helps keep the data more complete
by making it easier to modify for coverage of bug cases
that exist in production data.
And since the data becomes easier to modify,
the tests around it become easier to write,
which means few mistakes and few bugs.

The records
-----------

Records are stored in a directory structure by schema version.
The record file names are by table name and primary key(s).
For example,
a piece of data from the modules table
with a module_ident (the primary key) of 1
would have the filename ``modules-1.json``

The internals of the record data structure are in JSON.
The object structure of a record looks like this::

    {"table": "",
     "primarykeys": [],
     "predepends": [],
     "record": {},
     "postdepends": [],
     "comments": ""
     }

The `table`, `primarykeys` and `record` values are required.
Everything else is optional.

Dependencies are listed as filenames.
"""
import os
import jsonpickle
from psycopg2 import Binary
from . import TESTING_DATA_DIRECTORY


__all__ = (
    'POPULATION_RECORDS_DIRECTORY',
    'populate_database',
    )


# See the README file in the population-records directory for more info.
POPULATION_RECORDS_DIRECTORY = os.path.join(TESTING_DATA_DIRECTORY,
                                            'population-records')


def to_sql_value(value):
    """Used to convert custom types to valid SQL input values."""
    if isinstance(value, FilePointer):
        with open(value.full_filepath, 'rb') as fb:
            value = Binary(fb.read())
    return value


class FilePointer(object):  # new-style class for jsonpickle's benefit.
    """This only exists because we can't jsonpickle filelike objects."""

    def __init__(self, filepath, root=POPULATION_RECORDS_DIRECTORY):
        self.filepath = filepath
        self.rel_root = os.path.relpath(root, TESTING_DATA_DIRECTORY)
        if not os.path.exists(self.full_filepath):
            message = "file can't be found at '{}'"
            raise ValueError(message.format(self.full_filepath))

    @property
    def full_filepath(self):
        return os.path.join(TESTING_DATA_DIRECTORY,
                            self.rel_root, self.filepath)

    def read(self):
        with open(self.full_filepath, 'rb') as fb:
            return fb.read()


_record_file_cache = {}  # keyed by filepath, valued by record


class Record:

    def __init__(self, table, primarykeys, record,
                 predepends=[], postdepends=[], comments=''):
        self.table_name = table
        self.predepends = predepends
        self.postdepends = postdepends
        self.record = record
        self.primarykeys = primarykeys
        self.comments = ''

    @classmethod
    def from_file(cls, filepath, root=POPULATION_RECORDS_DIRECTORY):
        global _record_file_cache
        record_filepath = os.path.join(root, filepath)
        try:
            # Lookup the record from the cache.
            return _record_file_cache[record_filepath]
        except KeyError:
            pass

        with open(record_filepath, 'r') as record_file:
            try:
                record_data = jsonpickle.decode(record_file.read())
            except ValueError as exc:
                message = "{} || on {}".format(exc.message, record_filepath)
                raise ValueError(message)
        # Pop dependency info prior to caching the main record.
        # FIXME Using an object cache rather than a filename based cache
        #       would solve this "popping of dependencies before
        #       instantiation" issue.
        dependencies = {}
        for dep_step in ('predepends', 'postdepends',):
            try:
                dependencies[dep_step] = record_data.pop(dep_step)
            except KeyError:
                dependencies[dep_step] = []
        obj = cls(**record_data)
        setattr(obj, '_filepath', filepath)
        setattr(obj, '_root', root)
        # Cache the new record.
        _record_file_cache[record_filepath] = obj
        # Reassign dependency info
        for dep_step in ('predepends', 'postdepends',):
            dependencies[dep_step] = [
                cls.from_file(dep_filepath, root)
                for dep_filepath in dependencies[dep_step]
                ]
            setattr(obj, dep_step, dependencies[dep_step])
        return obj

    def exists(self, db_cursor):
        """Checks if the record exists in the database."""
        args = []
        conditions = []
        for key in self.primarykeys:
            conditions.append("{} = %s".format(key))
            args.append(self.record[key])
        conditions = ' AND '.join(conditions)
        formats = {'table_name': self.table_name,
                   'conditions': conditions,
                   }
        db_cursor.execute("SELECT * FROM {table_name} "
                          "  WHERE {conditions}".format(**formats),
                          args)
        record = db_cursor.fetchone()
        return record and True or False

    def push(self, db_cursor):
        """Given a database cursor, check if the record exists before
        attempting to insert its pre- and post- dependencies, as well
        as itself.
        """
        if self.exists(db_cursor):
            return

        for record in self.predepends:
            record.push(db_cursor)
        record_listing = [(k,v) for k,v in self.record.items()]
        record_keys, record_values = zip(*record_listing)
        formats = {'table_name': self.table_name,
                   'columns': ', '.join(record_keys),
                   'values': ', '.join(['%s'] * len(record_values)),
                   }
        # Reassign FilePointer to psycopg2.Binary values.
        record_values = [to_sql_value(v) for v in record_values]
        for i, value in enumerate(record_values):
            if isinstance(value, FilePointer):
                with open(value.full_filepath, 'rb') as fb:
                    record_values[i] = Binary(fb.read())
        db_cursor.execute("INSERT INTO {table_name} ({columns}) "
                          "  VALUES ({values});".format(**formats),
                          record_values)
        for record in self.postdepends:
            record.push(db_cursor)
        return


def populate_database(db_connection, record_filepaths=[],
                      root=POPULATION_RECORDS_DIRECTORY):
    """Populate the database using the given database connection
    and a list of records.
    """
    # This will in some cases create duplicate records, because the class
    #   isn't setup in such a way that it creates records in a shared
    #   contextual space. This is fine, since the records do insert-prechecks.
    #   There may be a slight expense for this behavior, but we can handle it.
    #   Besides, this implementation is only for testing purposes.
    with db_connection.cursor() as cursor:
        for filepath in record_filepaths:
            full_filepath = os.path.join(root, filepath)
            fileroot = os.path.dirname(full_filepath)
            filename = os.path.basename(full_filepath)
            record = Record.from_file(filename, fileroot)
            record.push(cursor)
            db_connection.commit()
