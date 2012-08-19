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
		self.accounts[merchant] = transactions

class Merchant(object):
	_merchants = dict()

	def __init__(self, id, name):
		self.id = id
		self.name = name

	@classmethod
	def from_row(cls, row):
		id = row['Merchant ID']
		name = row['DBA Name'].strip()
		merchant = cls._merchants.setdefault(id, cls(id, name))
		return merchant

	def __repr__(self):
		return '{name} ({id})'.format(**vars(self))

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

def build_portfolio():
	"Build a portfolio from a report"
	portfolio = Portfolio()
	try:
		with open('portfolio.pickle', 'rb') as pfp:
			portfolio = pickle.load(pfp)
	except:
		pass
	import sys
	filename = sys.argv[1]
	report = load_report(filename)
	for agent in report:
		agent_lgr = portfolio.setdefault(agent, ledger.Ledger())
		for merchant, residuals in agent.accounts.iteritems():
			for residual in residuals:
				amount = parse_amount(residual.amount)
				date = residual.date.as_object()
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

	with open('portfolio.pickle', 'wb') as pfp:
		pickle.dump(portfolio, pfp, protocol=pickle.HIGHEST_PROTOCOL)
	portfolio.export('portfolio.xlsx')

if __name__ == '__main__':
	build_portfolio()
