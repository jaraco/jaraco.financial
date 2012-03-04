# -*- coding: UTF-8 -*-

"""
Financial tools
Copyright (c) 2010-2011 Jason R. Coombs
"""

import sys

import setuptools

name = 'jaraco.financial'

argparse_req = ['argparse'] if sys.version_info < (2, 7) else []
dateutil_ver = '<2.0dev' if sys.version_info < (3,) else '>=2.0'
dateutil_req = ['python-dateutil' + dateutil_ver]

setup_params = dict(
	name = name,
	use_hg_version = dict(increment='0.1'),
	description = 'Financial tools by jaraco',
	author = 'Jason R. Coombs',
	author_email = 'jaraco@jaraco.com',
	url = 'http://pypi.python.org/pypi/' + name,
	packages = setuptools.find_packages(),
	namespace_packages = ['jaraco', ],
	license = 'MIT',
	classifiers = [
		"Development Status :: 4 - Beta",
		"Intended Audience :: Developers",
		"Programming Language :: Python",
		"Programming Language :: Python :: 3",
	],
	entry_points = {
		'console_scripts': [
			'fix-qif-date-format = jaraco.financial.qif:fix_dates_cmd',
			'launch-in-money = jaraco.financial.msmoney:launch',
			'ofx = jaraco.financial.ofx:handle_command_line',
			'clean-msmoney-temp = jaraco.financial.msmoney:clean_temp',
			'record-document-hashes = jaraco.financial.records:send_hashes',
		],
	},
	install_requires=[
		'keyring',
		'jaraco.util',
	] + argparse_req + dateutil_req,
	extras_require = {
	},
	dependency_links = [
	],
	tests_require=[
	],
	setup_requires=[
		'hgtools>=0.4',
	],
	use_2to3=True,
)

if __name__ == '__main__':
	setuptools.setup(**setup_params)
