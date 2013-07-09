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

with open('README') as ldf:
	long_description = ldf.read()

setup_params = dict(
	name = name,
	use_hg_version = True,
	description = 'Financial tools by jaraco',
	long_description = long_description,
	author = 'Jason R. Coombs',
	author_email = 'jaraco@jaraco.com',
	url = 'http://pypi.python.org/pypi/' + name,
	packages = setuptools.find_packages(),
	namespace_packages = ['jaraco', ],
	license = 'MIT',
	classifiers = [
		"Development Status :: 4 - Beta",
		"Intended Audience :: Developers",
		"Programming Language :: Python :: 2.6",
		"Programming Language :: Python :: 2.7",
		"Programming Language :: Python :: 3",
	],
	entry_points = {
		'console_scripts': [
			'fix-qif-date-format = jaraco.financial.qif:fix_dates_cmd',
			'launch-in-money = jaraco.financial.msmoney:launch_cmd',
			'ofx = jaraco.financial.ofx:handle_command_line',
			'clean-msmoney-temp = jaraco.financial.msmoney:clean_temp',
			'record-document-hashes = jaraco.financial.records:send_hashes',
			'cornerstone-portfolio = jaraco.financial.merchant:'
				'Portfolio.handle_command_line',
		],
	},
	install_requires=[
		'keyring',
		'jaraco.util>=6.3.1',
		'path.py',
		'ofxparse',
		'requests',
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
)

if __name__ == '__main__':
	setuptools.setup(**setup_params)
