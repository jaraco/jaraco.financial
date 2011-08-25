# -*- coding: UTF-8 -*-

"""
Financial tools
Copyright (c) 2010-2011 Jason R. Coombs
"""

import sys

import setuptools

name = 'jaraco.financial'

argparse_req = ['argparse'] if sys.version_info < (2,7) else []

setup_params = dict(
	name = name,
	use_hg_version = dict(increment='0.1'),
	description = 'Financial tools by jaraco',
	author = 'Jason R. Coombs',
	author_email = 'jaraco@jaraco.com',
	url = 'http://pypi.python.org/pypi/'+name,
	packages = setuptools.find_packages(),
	namespace_packages = ['jaraco',],
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
		],
	},
	install_requires=[
		'keyring',
		'jaraco.util',
	] + argparse_req,
	extras_require = {
	},
	dependency_links = [
	],
	tests_require=[
	],
	setup_requires=[
		'hgtools>=0.4',
	],
	use2to3=True,
)

if __name__ == '__main__':
	setuptools.setup(**setup_params)
