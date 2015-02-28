import re
import time
import textwrap

from jaraco.collections import DictAdapter

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

def DALS(str):
	"dedent and left strip"
	return textwrap.dedent(str).lstrip()

class Transaction(object):
	fmt = DALS("""
		!Type:{type}
		D{qif_date}
		T{amount}
		""")

	def _as_mapping(self):
		return DictAdapter(self)

class InvestmentTransaction(Transaction):
	fmt = Transaction.fmt + DALS("""
		N{inv_type}
		Y{fund}
		I{price}
		Q{quantity}
		^
		""")

	def qif_str(self):
		return self.fmt.format(self._as_mapping())
