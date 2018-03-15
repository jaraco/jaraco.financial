"""
Resolve sales from transactions using LIFO
"""

import sys
import csv
import functools
import re
import decimal
import itertools
import collections

from jaraco.functools import compose
from more_itertools.recipes import consume
import autocommand


write = functools.partial(open, 'w')


class Lots(collections.defaultdict):
	date_field = 'Timestamp'
	type_field = 'Transaction Type'
	qty_field = 'Quantity Transacted'
	asset_field = 'Asset'
	amount_field = 'USD Amount Transacted (Inclusive of Coinbase Fees)'
	buy_pattern = '(Buy|Receive)'
	basis_field = 'Basis'

	def __init__(self, transactions):
		self.transactions = transactions
		self.lot_count = itertools.count(1)
		super().__init__(list)

	def __iter__(self):
		for transaction in self.transactions:
			yield from self.handle_transaction(transaction)

	def handle_transaction(self, transaction):
		is_buy = re.match(self.buy_pattern, transaction[self.type_field])
		if is_buy:
			transaction['Lot'] = next(self.lot_count)
		yield dict(transaction)
		if is_buy:
			transaction[self.qty_field] = decimal.Decimal(transaction[self.qty_field])
			self[transaction[self.asset_field]].append(transaction)
			return

		yield from self.allocate_lots(transaction)

	def allocate_lots(self, sale):
		remainder = sale_qty = decimal.Decimal(sale[self.qty_field])
		asset = sale[self.asset_field]
		while remainder > decimal.Decimal():
			try:
				last = self[asset].pop(-1)
				last.setdefault('orig_qty', last[self.qty_field])
			except IndexError:
				print(f"Warning! No lots for {asset}", file=sys.stderr)
				return
			alloc = min(remainder, last[self.qty_field])
			last[self.qty_field] -= alloc
			remainder -= alloc
			amount = alloc / sale_qty * decimal.Decimal(sale[self.amount_field])
			basis = alloc / last['orig_qty'] * decimal.Decimal(last[self.amount_field])
			yield {
				self.qty_field: alloc,
				self.date_field: last[self.date_field],
				self.type_field: f'{sale[self.type_field]} Lot {last["Lot"]}',
				self.amount_field: round(amount, 2),
				self.basis_field: round(basis, 2),
			}
			if last[self.qty_field] > decimal.Decimal():
				self[asset].append(last)


DictWriter = functools.partial(csv.DictWriter, fieldnames=None)


@autocommand.autocommand(__name__)
def run(
	input: compose(csv.DictReader, open)=csv.DictReader(sys.stdin),
	output: compose(DictWriter, write)=DictWriter(sys.stdout),
	skip: int=3,
):
	"""
	Resolve sales from transactions using LIFO strategy.
	"""
	output.writer.writerows(itertools.islice(input.reader, skip))
	output.fieldnames = ['Lot'] + input.fieldnames + [Lots.basis_field]
	output.writeheader()
	consume(map(output.writerow, Lots(input)))
