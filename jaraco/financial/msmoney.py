from __future__ import print_function, unicode_literals, absolute_import

import argparse
import subprocess
import os
import re

from path import path

def find_programfiles_dir(child):
	"""
	Find a file in Program Files or Program Files (x86)
	"""
	pgfiles = path(r'C:\Program Files'), path(r'C:\Program Files (x86)')
	candidates = (root / child for root in pgfiles)
	return next(candidate for candidate in candidates if candidate.isdir())

def find_money():
	root = find_programfiles_dir('Microsoft Money Plus')
	return root / 'MnyCoreFiles' / 'mnyimprt.exe'

def get_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('filename')
	return parser.parse_args()

def launch():
	"Command-line script to launch a file in MS Money"
	money = find_money()
	args = get_args()
	subprocess.Popen([money, args.filename])

def clean_temp():
	"""
	Sometimes, Money will crash on an invalid file, and the only way to get it
	start is to clean the registry or remove the files. This technique
	removes the files, and Money will clean the registry on the next start.
	"""
	to_remove = [
		f for f in path(os.environ['TEMP']).files()
		if re.match(r'~of[0-9A-Z]{4}\.tmp', f.basename())
	]
	for f in to_remove:
		print('removing', f)
		f.remove()
