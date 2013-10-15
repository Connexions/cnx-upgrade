# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


install_requires = (
    'cnx-archive',
    'psycopg2',
    )
tests_require = (
    'jsonpickle',
    )
extras_require = {
    'test': tests_require,
    }
description = "An upgrade utility"


setup(
    name='cnx-upgrade',
    version='0.1',
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-upgrade",
    license='LGPL, See aslo LICENSE.txt',
    description=description,
    packages=find_packages(),
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    include_package_data=True,
    entry_points="""\
    [console_scripts]
    cnx-upgrade = cnxupgrade.cli:main
    cnx-upgrade-buylinks = cnxupgrade.buylinks:main
    """,
    test_suite='cnxupgrade.tests',
    )
