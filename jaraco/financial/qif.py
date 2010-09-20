import re
import sys
import time

def get_locale_time(date):
	# consider instead GetLocaleInfo
	import win32api
	LOCALE_USER_DEFAULT = 0x400
	flags = 0
	return win32api.GetDateFormat(LOCALE_USER_DEFAULT, flags, date)


def replace_val(matcher):
	date = time.strptime(matcher.group(0), 'D%m/%d/%Y')
	return 'D'+time.strftime('%d-%m-%Y', date)

def inline_sub(filename):
	dat = open(filename).read()
	# here's the pattern Paypal sends my QIF dates in
	pattern = '^D\d+/\d+/\d{2,4}$'
	pattern = re.compile(pattern, re.MULTILINE)
	res = pattern.sub(replace_val, dat)
	open(filename, 'w').write(res)

def fix_dates_cmd():
	from optparse import OptionParser
	parser = OptionParser(usage="%prog filename")
	options, args = parser.parse_args()
	filename = args.pop()
	if args: parser.error("Unexpected parameter")
	inline_sub(filename)
