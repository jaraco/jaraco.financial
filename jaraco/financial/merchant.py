from __future__ import print_function, unicode_literals

import re
import collections

from bs4 import BeautifulSoup
import path

def run():
	doc = path.path('//drake/users/jaraco/Downloads/'
		'TLReport_PortfolioFinancialNetProfitMultiMonth_CPL-001.xls').expanduser()
	with open(doc) as f:
		data = f.read()
	data = '<html>'+data+'</html>'
	soup = BeautifulSoup(data)

	tables = map(parse_table, soup.find_all('table'))
	assert len(tables) == 1
	table = tables[0]
	agents = map(Agent.from_row, table)
	map(print, agents)

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
		dates = filter(None, map(Date.from_key, row))
		return [Transaction(date, row[date]) for date in dates]

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


def get_agents(table):
	return map(Agent.from_row, table)

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

if __name__ == '__main__':
	run()
