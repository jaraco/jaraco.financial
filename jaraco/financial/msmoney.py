import argparse
import subprocess
import itertools
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
