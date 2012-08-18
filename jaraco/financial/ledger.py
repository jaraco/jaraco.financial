import bisect
import datetime

import jaraco.util.itertools

class Transaction(object):
	payee = None
	date = None
	designation = None
	"SimpleDesination, SplitDesignation, or Ledger"
	source = None
	"Where was this transaction sourced ('manual', 'bank download')"

	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)
		if not 'date' in vars(self):
			self.date = datetime.datetime.utcnow()

	@property
	def amount(self):
		"""
		The total of the amounts of the designations of this transaction.
		"""
		return sum(
			item.amount
			for item in jaraco.util.itertools.always_list(self.designation)
		)

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
	def add(self, item):
		bisect.insort_right(self, item)

class Named(object):
	def __init__(self, name, *args, **kwargs):
		super(Named, self).__init__(*args, **kwargs)
		self.name = name

class Account(Named, Ledger):
	"""
	A named ledger
	"""
