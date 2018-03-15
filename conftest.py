import sys


collect_ignore = []

collect_ignore += [
	'jaraco/financial/paychex.py',
	'jaraco/financial/lifo.py',
] if sys.version_info < (3,) else []
