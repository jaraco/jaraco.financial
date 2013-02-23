"""
A collection of Merchant-processing routines for Cornerstone, LLC.
"""

from __future__ import print_function, unicode_literals, division

import re
import collections
import pickle
import decimal
import datetime
import itertools

from jaraco.util.itertools import is_empty
from bs4 import BeautifulSoup
import xlsxcessive.xlsx

from . import ledger

def load_report(source):
	"""
	Load a report as downloaded from Translink
	"""
	with open(source) as f:
		data = f.read()
	data = '<html>'+data+'</html>'
	soup = BeautifulSoup(data)

	tables = map(parse_table, soup.find_all('table'))
	assert len(tables) == 1
	table = tables[0]
	agents = set(map(Agent.from_row, table))

	return agents

def indent(lines):
	return ['  ' + line for line in lines]

class Agent(object):
	_agents = dict()

	def __init__(self, id, name):
		self.id = id
		self.name = name
		self.accounts = dict()

	def __repr__(self):
		return '{name} ({id})'.format(**vars(self))

	def __str__(self):
		return str(unicode(self))

	def __unicode__(self):
		lines = [repr(self)]
		lines.extend(indent(self.merchant_lines()))
		return '\n'.join(lines)

	def merchant_lines(self):
		for merchant in self.accounts:
			yield unicode(merchant)
			for line in indent(map(unicode, self.accounts[merchant])):
				yield line

	@classmethod
	def from_row(cls, row):
		id = row['Sales Rep Number'].strip()
		name = row['Sales Rep Name'].strip()
		agent = cls._agents.setdefault(id, cls(id, name))
		agent.add_row(row)
		return agent

	def add_row(self, row):
		merchant = Merchant.from_row(row)
		transactions = Transaction.from_row(row)
		by_date = lambda txn: txn.date.as_object()
		self.accounts[merchant] = sorted(transactions, key=by_date)

	def __hash__(self):
		"""
		Provide a hash for uniquely identifying agents.
		"""
		return hash(self.id)

	def __eq__(self, other):
		return self.id == other.id


class Merchant(object):
	_merchants = dict()

	def __init__(self, id, name, association_number):
		self.id = id
		self.name = name
		self.association_number = association_number

	@classmethod
	def from_row(cls, row):
		id = row['Merchant ID']
		name = row['DBA Name'].strip()
		assoc = row['Association Number'].strip()
		merchant = cls._merchants.setdefault(id, cls(id, name, assoc))
		return merchant

	def __repr__(self):
		return '{name} ({id})'.format(**vars(self))

	@property
	def association_name(self):
		return {
			'096367': 'advance',
			'096403': 'residual',
			'096590': 'simple',
		}[self.association_number]

class Transaction(object):
	def __init__(self, date, amount):
		self.date = date
		self.amount = amount

	@classmethod
	def from_row(cls, row):
		return [
			Transaction(date, row[date])
			for date in map(Date.from_key, row)
			if date and row[date] != '$0.00'
		]

	def __repr__(self):
		return 'Transaction({date}, {amount})'.format(**vars(self))

	def __unicode__(self):
		return repr(self)

class Date(unicode):
	@classmethod
	def from_key(cls, key):
		if not re.match('\d+/\d+', key):
			return None
		return cls(key)

	def as_object(self):
		"Return self as a datetime.date object (1st of the month)"
		month, year = map(int, self.split('/'))
		return datetime.date(year, month, 1)

def data(row):
	return [
		node.text for node in row.find_all('td')
	]

def parse_table(node):
	rows = iter(node.find_all('tr'))
	header = data(next(rows))
	rows = [collections.OrderedDict(zip(header, data(row)))
		for row in rows]
	return rows

def parse_amount(amount_str):
	"""
	>>> parse_amount('$20.0')
	20.0
	>>> parse_amount('(30)')
	-30
	>>> parse_amount('($30.1)')
	-30.1
	"""
	amount_str = amount_str.replace('$', '').replace(',', '')
	if amount_str.startswith('(') and amount_str.endswith(')'):
		amount_str = '-'+amount_str.strip('()')
	return decimal.Decimal(amount_str)

class SheetWriter(object):
	def __init__(self, sheet):
		self.sheet = sheet
		self.row_count = itertools.count()

	def write(self, *values):
		row = next(self.row_count)
		for col, value in enumerate(values):
			self.sheet.cell(coords=(row, col), value=value)

class Portfolio(dict):
	def export(self, filename):
		workbook = xlsxcessive.xlsx.Workbook()
		for agent, agent_lgr in self.iteritems():
			sheet = workbook.new_sheet(agent.name)
			w = SheetWriter(sheet)
			w.write('Date', 'Payee', 'Category', 'Amount')
			for txn in agent_lgr:
				w.write(txn.date, None, txn.designation.descriptor,
					txn.amount)
		xlsxcessive.xlsx.save(workbook, filename)

	def build(self):
		"Build a portfolio from a report"
		try:
			with open('portfolio.pickle', 'rb') as pfp:
				self = pickle.load(pfp)
		except Exception:
			pass
		import sys
		filename = sys.argv[1]
		report = load_report(filename)
		for agent in report:
			agent_lgr = self.setdefault(agent, ledger.Ledger())
			# keep track of the dates where transactions occurred
			dates = set()
			for merchant, residuals in agent.accounts.iteritems():
				for residual in residuals:
					amount = parse_amount(residual.amount)
					date = residual.date.as_object()
					dates.add(date)
					designation = ledger.SimpleDesignation(
						descriptor = "Residuals Earned : " + unicode(merchant),
						amount = amount,
						)
					txn = ledger.Transaction(date=date,
						designation=designation)
					txn.source = 'ISO statement'

					if txn in agent_lgr:
						# skip transactions that are already an exact match
						print('.', end='')
						continue

					agent_lgr.add(txn)
					# pay share to Cornerstone
					designation = ledger.SimpleDesignation(
						descriptor = "Residuals Shared : " + unicode(merchant),
						amount = -txn.amount / 2,
					)
					txn = ledger.Transaction(date=date,
						designation=designation)
					txn.source = 'calculated'
					agent_lgr.add(txn)

					self.account_for_advances(merchant, agent_lgr, date,
						amount)
			[self.pay_balance(agent_lgr, date) for date in sorted(dates)]

		with open('portfolio.pickle', 'wb') as pfp:
			pickle.dump(self, pfp, protocol=pickle.HIGHEST_PROTOCOL)
		self.export('portfolio.xlsx')

	def pay_balance(self, agent_lgr, date):
		"""
		For the given date, calculate the balance through that date and add a
		transaction on that date to bring the account balance to zero.
		"""
		balance = agent_lgr.balance_through(date)
		designation = ledger.SimpleDesignation(
			descriptor = "Commissions Paid",
			amount = -balance,
		)
		txn = ledger.Transaction(date=date, designation=designation)
		agent_lgr.add(txn)

	def account_for_advances(self, merchant, agent_lgr, date, amount):
		"account for advances"

		if merchant.association_name == 'simple':
			# don't account for advances with simple merchant associations
			return

		# first add the $200 advance (200 shared with cornerstone)
		# if it's not already present
		advance_descriptor = "Residual Advance : " + unicode(merchant)
		add_advance = is_empty(
			agent_lgr.query(descriptor=advance_descriptor, amount=200)
		)
		if add_advance:
			designation = ledger.SimpleDesignation(
				descriptor = advance_descriptor,
				amount = 200,
			)
			txn = ledger.Transaction(date=date,
				designation = designation)
			txn.source = 'inferred'
			agent_lgr.add(txn)

		# now deduct any outstanding advances
		advance_txns = agent_lgr.query(descriptor=advance_descriptor)
		outstanding = sum(
			txn.get_amount(descriptor=advance_descriptor)
			for txn in advance_txns)
		if outstanding > 0:
			# amount to repay
			repay_adv = -min(outstanding, amount / 2)
			designation = ledger.SimpleDesignation(
				descriptor = advance_descriptor, amount=repay_adv)
			txn = ledger.Transaction(date=date,
				designation = designation)
			txn.source = 'calculated'
			agent_lgr.add(txn)

if __name__ == '__main__':
	Portfolio().build()
