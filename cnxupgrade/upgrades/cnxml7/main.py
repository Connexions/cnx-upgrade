# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import psycopg2

from .utils import determine_cnxml_version, normalize_xml
from .transforms import upgrade_document


__all__ = ('main',)


SQL_BUTTER_FUNCTION = """\
CREATE OR REPLACE FUNCTION butter (file BYTEA) RETURNS TEXT AS $$
DECLARE
  value TEXT;
BEGIN
  BEGIN
    value := convert_from(file, 'utf-8');
  EXCEPTION
    WHEN character_not_in_repertoire THEN
      -- try again...
      BEGIN
        value := convert_from(file, 'latin1');
      EXCEPTION
        WHEN character_not_in_repertoire THEN
          value := "ENCODING ERROR";
      END;
  END;
  RETURN value;
END;
$$ LANGUAGE plpgsql;
"""


def main(db_connection, filename='index_auto_generated.cnxml'):
    """Upgrade CNXML documents to version 0.7 and normalize them into the
    given filename, which will be entered into the database.
    """
    with db_connection.cursor() as cursor:
        # Inject some encoding butter.
        cursor.execute(SQL_BUTTER_FUNCTION)

        # Grab cursory info about modules for iteration and logging.
        cursor.execute("SELECT moduleid, version, module_ident "
                       "FROM latest_modules "
                       "     NATURAL LEFT JOIN module_files AS mf "
                       "WHERE portal_type = 'Module' "
                       "      AND mf.filename = 'index.cnxml' "
                       "ORDER BY module_ident ASC;")
        records = cursor.fetchall()

        for record in records:
            mid, version, ident = record
            cursor.execute("SELECT butter(file) "
                           "FROM module_files NATURAL LEFT JOIN files "
                           "WHERE module_ident = %s "
                           "      AND filename = 'index.cnxml';",
                           (ident,))
            file = cursor.fetchone()[0]

            # Is it valid XML?
            pass

            # Can we determine the CNML version?
            try:
                cnxml_version = determine_cnxml_version(file)
            except:
                # Probably a deeper problem with the document itself.
                #   Fail and move on.
                cnxml_version, state = '?', False
                message = 'problem determining CNXML version'
            else:
                # Try to upgrade the document...
                source, was_upgraded, error_messages = upgrade_document(file)
                if was_upgraded or cnxml_version == '0.7':
                    file = normalize_xml(file)
                    cursor.execute("INSERT INTO files (file) VALUES (%s) "
                                   "RETURNING fileid;",
                                   (psycopg2.Binary(file),))
                    fileid = cursor.fetchone()[0]
                    cursor.execute("INSERT INTO module_files "
                                   "(module_ident, fileid, filename, mimetype) "
                                   "VALUES (%s, %s, 'index_auto_generated.cnxml', 'text/xml');",
                                   (ident, fileid,))
                    db_connection.commit()
                    state, message = True, ''
                else:
                    # Determine why... Errors are only sent out to stderr
                    state, message = False, error_messages

            processed = (mid, version, ident, cnxml_version, state, message,)
            yield processed

        # Melt the butter.
        cursor.execute("DROP FUNCTION butter(BYTEA);")

        raise StopIteration
