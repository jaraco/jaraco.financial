from __future__ import print_function, unicode_literals, absolute_import

import argparse
import subprocess
import os
import re
import sys

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

def patch_binary_for_payee_name_crash():
	"""
	In `this blog entry
	<http://blogs.msdn.com/b/oldnewthing/archive/2012/11/13/10367904.aspx>`,
	the author has reverse-engineered the buggy MS Money code and devised
	a fix by altering the binary. This method applies that patch
	programmatically, doing some sanity checks to not incorrectly patch.

	File offset 003FACE8: Change 85 to 8D
	File offset 003FACED: Change 50 to 51
	File offset 003FACF0: Change FF to 85
	File offset 003FACF6: Change E8 to B9
	"""
	prog_dir = find_programfiles_dir('Microsoft Money Plus') / 'MnyCoreFiles'
	dll = prog_dir / 'mnyob99.dll'
	# back up the file
	backup = prog_dir / 'mnyob99.dll.bak'
	if backup.exists():
		print("Backup already exists", file=sys.stderr)
		raise SystemExit(1)
	dll.copyfile(backup)
	# open the file for read and update (binary)
	with dll.open('r+b') as file:
		file.seek(0x3FACE8)
		data = file.read(0xF6-0xE8+1)
		assert ord(data[0xE8-0xE8]) == 0x85
		assert ord(data[0xED-0xE8]) == 0x50
		assert ord(data[0xF0-0xE8]) == 0xFF
		assert ord(data[0xF6-0xE8]) == 0xE8
		file.seek(0x3FACE8)
		file.write(chr(0x8D))
		file.seek(0x3FACED)
		file.write(chr(0x51))
		file.seek(0x3FACF0)
		file.write(chr(0x85))
		file.seek(0x3FACF6)
		file.write(chr(0xB9))
