#!/usr/bin/env python
# Generated by jaraco.develop 2.23
# https://pypi.python.org/pypi/jaraco.develop

import io
import sys

import setuptools

with io.open('README.txt', encoding='utf-8') as readme:
	long_description = readme.read()

needs_pytest = {'pytest', 'test'}.intersection(sys.argv)
pytest_runner = ['pytest_runner'] if needs_pytest else []
needs_sphinx = {'release', 'build_sphinx', 'upload_docs'}.intersection(sys.argv)
sphinx = ['sphinx'] if needs_sphinx else []
needs_wheel = {'release', 'bdist_wheel'}.intersection(sys.argv)
wheel = ['wheel'] if needs_wheel else []

setup_params = dict(
	name='jaraco.financial',
	use_scm_version=True,
	author="Jason R. Coombs",
	author_email="jaraco@jaraco.com",
	description="jaraco.financial",
	long_description=long_description,
	url="https://bitbucket.org/jaraco/jaraco.financial",
	packages=setuptools.find_packages(),
	include_package_data=True,
	namespace_packages=['jaraco'],
	install_requires=[
		'keyring',
		'path.py',
		'ofxparse',
		'requests',
		'jaraco.itertools',
		'jaraco.logging',
		'jaraco.ui',
		'jaraco.text',
		'jaraco.collections',
		'python-dateutil>=2.0',
	],
	extras_require={
	},
	setup_requires=[
		'setuptools_scm>=1.9',
	] + pytest_runner + sphinx + wheel,
	tests_require=[
		'pytest>=2.8',
	],
	classifiers=[
		"Development Status :: 5 - Production/Stable",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: MIT License",
		"Programming Language :: Python :: 2.7",
		"Programming Language :: Python :: 3",
	],
	entry_points={
		'console_scripts': [
			'fix-qif-date-format = jaraco.financial.qif:fix_dates_cmd',
			'launch-in-money = jaraco.financial.msmoney:launch_cmd',
			'ofx = jaraco.financial.ofx:handle_command_line',
			'clean-msmoney-temp = jaraco.financial.msmoney:clean_temp',
			'record-document-hashes = jaraco.financial.records:send_hashes',
		],
	},
)
if __name__ == '__main__':
	setuptools.setup(**setup_params)
