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
import argparse
import operator

from jaraco.util.itertools import is_empty
from jaraco.util import ui
from bs4 import BeautifulSoup
import xlsxcessive.xlsx

from . import ledger

class TranslinkReport(set):
	@classmethod
	def load(cls, stream):
		"""
		Load a set of agents from a Translink .xls report
		"""
		data = stream.read()
		data = '<html>'+data+'</html>'
		soup = BeautifulSoup(data)

		tables = map(parse_table, soup.find_all('table'))
		assert len(tables) == 1
		table = tables[0]
		return cls(map(Agent.from_row, table))

def indent(lines):
	return ['  ' + line for line in lines]

class Obligation(collections.namedtuple('BaseObligation', 'agent share')):
	def __str__(self):
		return '{pct:.0f}% to {agent}'.format(
			agent=self.agent, pct=self.share*100)

class Obligations(dict):
	"""
	Map of merchant to set of Obligations
	"""

	def add(self, merchant, agent, share=0.5):
		ob = Obligation(agent, decimal.Decimal(share))
		self.setdefault(merchant, set()).add(ob)

class Agent(object):
	earn_rate = decimal.Decimal(0.5)
	"percent of residual agent keeps"

	_agents = dict()

	def __init__(self, id, name):
		self.id = id
		self.name = name
		self.accounts = dict()
		self.obligations = Obligations()

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
		transactions = AccountTransaction.from_row(row)
		by_date = lambda txn: txn.date.as_object()
		self.accounts[merchant] = sorted(transactions, key=by_date)

	def share_residuals(self, my_lgr, merchant, date, amount):
		"pay share to Cornerstone"

		share_rate = 1 - self.earn_rate
		designation = ledger.SimpleDesignation(
			descriptor = "Residuals Shared : " + unicode(merchant),
			amount = -amount*share_rate,
		)
		txn = ledger.Transaction(date=date, payee='Cornerstone',
			designation=designation)
		txn.source = 'calculated'
		my_lgr.add(txn)

		remainder = amount + txn.amount
		# share the remainder per obligations

		if merchant in self.obligations:
			for ob in self.obligations[merchant]:
				designation = ledger.SimpleDesignation(
					descriptor = "Residuals Shared : " + unicode(merchant),
					amount = -remainder * ob.share)

				txn = ledger.Transaction(date=date, payee=ob.agent.name,
					designation=designation)
				txn.source = 'calculated'
				my_lgr.add(txn)

				# TODO: add the inverse transaction into the other agent's lgr
				# get_ledger(ob.agent).add(...)

	def __hash__(self):
		"""
		Provide a hash for uniquely identifying agents.
		"""
		return hash(self.id)

	def __eq__(self, other):
		return self.id == other.id


class Merchant(object):
	_merchants = dict()
	prefix = '543684555'

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
		prefix, none, short_id = self.id.rpartition(self.prefix)
		return '{name} ({id})'.format(name=self.name, id=short_id)

	@property
	def association_name(self):
		return {
			'096367': 'advance',
			'096403': 'residual',
			'096590': 'simple',
		}[self.association_number]

class AccountTransaction(object):
	"""
	A specific transaction on an agent's account.
	"""

	def __init__(self, date, amount):
		self.date = date
		self.amount = amount

	@classmethod
	def from_row(cls, row):
		return [
			cls(date, row[date])
			for date in map(Date.from_key, row)
			if date and row[date] != '$0.00'
		]

	def __repr__(self):
		return 'AccountTransaction({date}, {amount})'.format(**vars(self))

	def __unicode__(self):
		return repr(self)

	def __hash__(self):
		return hash(self.date) + hash(self.amount)

	def __eq__(self, other):
		return self.date == other.date and self.amount == other.amount

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
		return [
			self.sheet.cell(coords=(row, col), value=value)
			for col, value in enumerate(values)
		]

class Portfolio(dict):
	@classmethod
	def load(cls):
		try:
			with open('portfolio.pickle', 'rb') as pfp:
				return pickle.load(pfp)
		except Exception:
			pass
		return cls()

	def export(self, filename):
		workbook = xlsxcessive.xlsx.Workbook()
		currency = workbook.stylesheet.new_format()
		currency.number_format('"$"#,##0.00')
		for agent, agent_lgr in self.iteritems():
			sheet = workbook.new_sheet(agent.name)
			sheet.col(number=1, width=11)
			sheet.col(number=3, width=65)
			sheet.col(number=4, width=10)
			w = SheetWriter(sheet)
			w.write('Date', 'Payee', 'Category', 'Amount')
			for txn in agent_lgr:
				cells = w.write(txn.date, txn.payee, txn.designation.descriptor,
					txn.amount)
				cells[-1].format = currency
		xlsxcessive.xlsx.save(workbook, filename)

	def import_(self, tl_report):
		"Import transactions from a TranslinkReport"
		for agent in tl_report:
			self.setdefault(agent, ledger.Ledger())

	def add_obligations(self):
		print("Agent obligations are:")
		for agent in self:
			if not agent.obligations:
				continue
			print(agent)
			for merchant in agent.obligations:
				print('  For', merchant)
				obl = agent.obligations[merchant]
				for obl in agent.obligations[merchant]:
					print('    ', obl)
		while True:
			if raw_input('Add new obligation? ') != 'y':
				break
			agent_menu = ui.Menu(list(self),
				formatter=operator.attrgetter('name'))
			agent = agent_menu.get_choice('which agent? ')
			merchant_menu = ui.Menu(list(agent.accounts),
				formatter=operator.attrgetter('name'))
			merchant = merchant_menu.get_choice('which merchant? ')
			other_agents = set(self) - set([agent])
			agent_menu = ui.Menu(list(other_agents),
				formatter=operator.attrgetter('name'))
			obl_agent = agent_menu.get_choice('pays to whom? ')
			amount = raw_input('what percentage? ')
			amount = int(amount)/100
			agent.obligations.add(merchant=merchant, agent=obl_agent,
				share=amount)

	def process_residuals(self):
		for agent in self:
			self._process_agent_residuals(agent)

	def _process_agent_residuals(self, agent):
		agent_lgr = self[agent]
		for merchant, residuals in agent.accounts.iteritems():
			for residual in residuals:
				amount = parse_amount(residual.amount)
				date = residual.date.as_object()
				designation = ledger.SimpleDesignation(
					descriptor = "Residuals Earned : " + unicode(merchant),
					amount = amount,
					)
				txn = ledger.Transaction(date=date, payee='TransLink',
					designation=designation)
				txn.source = 'ISO statement'

				if txn in agent_lgr:
					# skip transactions that are already an exact match
					continue

				agent_lgr.add(txn)
				agent.share_residuals(agent_lgr, merchant, date, txn.amount)
				self.account_for_advances(merchant, agent_lgr, date,
					amount)

	def pay_balances(self):
		dates = sorted(set(txn.date
			for ledger in self.itervalues()
			for txn in ledger
			if txn.date.day == 1
		))
		for date in dates:
			for agent_lgr in self.itervalues():
				self.pay_balance(agent_lgr, date)

	def save(self):
		with open('portfolio.pickle', 'wb') as pfp:
			pickle.dump(self, pfp, protocol=pickle.HIGHEST_PROTOCOL)

	def pay_balance(self, agent_lgr, date):
		"""
		For the given date, calculate the balance through that date and add a
		transaction on that date to bring the account balance to zero.
		"""
		balance = agent_lgr.balance_through(date)
		if balance == 0:
			return
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
			txn = ledger.Transaction(date=date, payee='TransLink',
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
			txn = ledger.Transaction(date=date, payee='TransLink',
				designation = designation)
			txn.source = 'calculated'
			agent_lgr.add(txn)

	@classmethod
	def handle_command_line(cls):
		parser = argparse.ArgumentParser()
		parser.add_argument('filename')
		args = parser.parse_args()
		portfolio = cls.load()
		with open(args.filename, 'rb') as pfb:
			tl_report = TranslinkReport.load(pfb)
			portfolio.import_(tl_report)
		portfolio.add_obligations()
		portfolio.process_residuals()
		portfolio.pay_balances()
		portfolio.save()
		portfolio.export('portfolio.xlsx')

if __name__ == '__main__':
	Portfolio().handle_command_line()
