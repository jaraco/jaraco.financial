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

	def get_amount(self, descriptor=None):
		"""
		The total of the amounts of the designations of this transaction
		that don't match the descriptor (or all if no descriptor supplied).
		"""
		return sum(
			item.amount
			for item in
				jaraco.util.itertools.always_iterable(self.designation)
			if descriptor is None or descriptor == item.descriptor
		)
	amount = property(get_amount)

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
		bisect.insort(self, item)

	@property
	def balance(self):
		return sum(txn.amount for txn in self)

	def query(self, descriptor=None, amount=None):
		for txn in self:
			dsgns = jaraco.util.itertools.always_iterable(txn.designation)
			for designation in dsgns:
				if descriptor and designation.descriptor != descriptor:
					continue
				if amount is not None and designation.amount != amount:
					continue
				yield txn
				# don't yield any transaction more than once
				break

class Named(object):
	def __init__(self, name, *args, **kwargs):
		super(Named, self).__init__(*args, **kwargs)
		self.name = name

class Account(Named, Ledger):
	"""
	A named ledger
	"""
