# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
This is a zope script used to extract module/collection hit records
from the ZODB to CSV file.

This outputs the CSV in the following format:

moduleid, total hits, recent hits, publication date, today, update interval

"""
import csv
import pytz
from datetime import datetime
import calendar

INTERVAL = 604800  # seconds (7 days), because hits are updated weekly


def _to_timestamp(dt):
    """datetime.datetime to timestamp"""
    return calendar.timegm(dt.utctimetuple())

def asdatetime(zdt):
    """Return a standard libary datetime.datetime
    """
    tzinfo = pytz.timezone(zdt.localZone())
    second = int(zdt._second)
    microsec = 0  ##zdt.micros() % 1000000
    dt = datetime(zdt._year, zdt._month, zdt._day, zdt._hour,
                  zdt._minute, second, microsec, tzinfo)
    return dt

def main():
    tool = app.plone.portal_hitcount
    output = csv.writer(sys.stdout)
    end_date = _to_timestamp(datetime.today())
    for obj_id, hit in tool._hits.items():
        start_date = _to_timestamp(asdatetime(hit.published))
        row = (obj_id, hit.total, hit.recent,
               start_date, end_date, INTERVAL,)
        output.writerow(row)


if __name__ == '__main__':
    main()
