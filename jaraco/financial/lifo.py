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

	def __init__(self, transactions):
		self.transactions = transactions
		super().__init__(list)

	def __iter__(self):
		for transaction in self.transactions:
			yield from self.handle_transaction(transaction)

	def handle_transaction(self, transaction):
		yield dict(transaction)
		if re.match(self.buy_pattern, transaction[self.type_field]):
			transaction[self.qty_field] = decimal.Decimal(transaction[self.qty_field])
			self[transaction[self.asset_field]].append(transaction)
			return

		yield from self.allocate_lots(transaction)

	def allocate_lots(self, sale):
		qty = decimal.Decimal(sale[self.qty_field])
		asset = sale[self.asset_field]
		while qty > decimal.Decimal():
			try:
				last = self[asset].pop(-1)
				last.setdefault('orig_qty', last[self.qty_field])
			except IndexError:
				print(f"Warning! No lots for {asset}", file=sys.stderr)
				return
			alloc = min(qty, last[self.qty_field])
			last[self.qty_field] -= alloc
			qty -= alloc
			amount = alloc / last['orig_qty'] * decimal.Decimal(last[self.amount_field])
			yield {
				self.qty_field: alloc,
				self.date_field: last[self.date_field],
				self.type_field: f'{sale[self.type_field]} Lot',
				self.amount_field: amount,
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
	output.fieldnames = input.fieldnames
	output.writeheader()
	consume(map(output.writerow, Lots(input)))
