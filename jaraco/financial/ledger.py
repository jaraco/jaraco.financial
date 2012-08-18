import bisect
import datetime

class Transaction(object):
	payee = None
	amount = None
	date = None
	designation = None
	source = None
	"Where was this transaction sourced ('manual', 'bank download')"

	def __init__(self, amount, **kwargs):
		self.amount = amount
		self.__dict__.update(kwargs)
		if not 'date' in vars(self):
			self.date = datetime.datetime.utcnow()

	# for the purpose of sorting transactions chronologically, sort by date
	def __lt__(self, other):
		return self.date < other.date

class SplitDesignation(list):
	"A list of SimpleDesignations"

class SimpleDesignation(object):
	def __init__(self, descriptor, amount, memo=None):
		self.descriptor = descriptor
		self.amount = amount
		self.memo = memo

class Ledger(list):
	"""
	A list of transactions, sorted by date.
	"""
	add = bisect.insort_right

class Named(object):
	def __init__(self, name, *args, **kwargs):
		super(Named, self).__init__(*args, **kwargs)
		self.name = name

class Account(Named, Ledger):
	"""
	A named ledger
	"""
