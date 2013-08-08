# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Upgrades for munging/transforming Connexions XML formats to HTML."""
import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import rhaptos.cnxmlutils
from lxml import etree
from psycopg2 import Binary


__all__ = (
    'cli_loader',
    'transform_collxml_to_html', 'transform_cnxml_to_html',
    'produce_html_for_collections',
    )


HTML_TEMPLATE_FOR_CNXML = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
{metadata}
{content}
</html>
"""
RHAPTOS_CNXMLUTILS_DIR = os.path.dirname(rhaptos.cnxmlutils.__file__)
XSL_DIRECTORY = os.path.abspath(os.path.join(RHAPTOS_CNXMLUTILS_DIR, 'xsl'))


def transform_cnxml_to_html(cnxml):
    """Transforms raw cnxml content to html."""
    gen_xsl = lambda f: etree.XSLT(etree.parse(f))
    cnxml = etree.parse(StringIO(cnxml))

    # Transform the content to html.
    cnxml_to_html_filepath = os.path.join(XSL_DIRECTORY, 'cnxml-to-html5.xsl')
    cnxml_to_html = gen_xsl(cnxml_to_html_filepath)
    content = cnxml_to_html(cnxml)

    # Transform the metadata to html.
    cnxml_to_html_metadata_filepath = os.path.join(
            XSL_DIRECTORY,
            'cnxml-to-html5-metadata.xsl')
    cnxml_to_html_metadata = gen_xsl(cnxml_to_html_metadata_filepath)
    metadata = cnxml_to_html_metadata(cnxml)

    html = HTML_TEMPLATE_FOR_CNXML.format(metadata=metadata, content=content)
    return html


def transform_collxml_to_html(collxml):
    """Transforms raw collxml content to html"""
    # XXX Temporarily return the same thing, worry about the transform
    #     after the higher level process works through.
    html = collxml
    return html


def produce_html_for_collections(db_connection):
    """Produce HTML files of existing collection documents. This will
    do the work on all collections in the database.

    Yields a state tuple after each collection is handled.
    The state tuple contains the id of the collection that was transformed
    and either None when no errors have occured
    or a message containing information about the issue.
    """
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT module_ident FROM modules "
                       "  WHERE portal_type = 'Collection';")
        # Note, the "ident" is different from the "id" in our tables.
        collection_idents = cursor.fetchall()

    for collection_ident in collection_idents:
        with db_connection.cursor() as cursor:
            # FIXME There is a better way to join this information, but
            #       for the sake of testing scope stick with the simple yet
            #       redundant lookups.
            cursor.execute("SELECT filename, fileid FROM module_files "
                           "  WHERE module_ident = %s;", (collection_ident,))
            file_metadata = dict(cursor.fetchall())
            file_id = file_metadata['collection.xml']
            # Grab the file for transformation.
            cursor.execute("SELECT file FROM files WHERE fileid = %s;",
                           (file_id,))
            collxml = cursor.fetchone()[0]
            collxml = collxml[:]
            collection_html = transform_collxml_to_html(collxml)
            # Insert the collection.html into the database.
            payload = (Binary(collection_html),)
            cursor.execute("INSERT INTO files (file) VALUES (%s) "
                           "RETURNING fileid;", payload)
            collection_html_file_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO module_files "
                           "  (module_ident, fileid, filename, mimetype) "
                           "  VALUES (%s, %s, %s, %s);",
                           (collection_ident, collection_html_file_id,
                            'collection.html', 'text/html',))
        yield (collection_ident, None)

    cursor.close()
    raise StopIteration


def cli_command():
    """The command used by the CLI to invoke the upgrade logic."""
    pass


def cli_loader(parser):
    """Used to load the CLI toggles and switches."""
    return cli_command
