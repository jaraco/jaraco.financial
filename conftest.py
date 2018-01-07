import sys


collect_ignore = []

collect_ignore += [
	'jaraco/financial/paychex.py',
] if sys.version_info < (3,) else []
