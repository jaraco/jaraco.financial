# -*- coding: UTF-8 -*-

"""
Financial tools
Copyright (c) 2010 Jason R. Coombs
"""

try:
	from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
	from distutils.command.build_py import build_py

from setuptools import setup, find_packages

name = 'jaraco.financial'

setup(
	name = name,
	use_hg_version = dict(increment='0.1'),
	description = 'Financial tools by jaraco',
	author = 'Jason R. Coombs',
	author_email = 'jaraco@jaraco.com',
	url = 'http://pypi.python.org/pypi/'+name,
	packages = find_packages(),
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
	],
	extras_require = {
	},
	dependency_links = [
	],
	tests_require=[
	],
	setup_requires=[
		'hgtools>=0.4',
	],
	cmdclass=dict(build_py=build_py),
)
