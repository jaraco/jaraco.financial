"""
Paychex, when they generate OFX downloads of their 401k account
data, their routine crashes and terminates output when it
encounters a Gain/Loss entry.

This routine takes instead the CSV output and generates a
proper OFX file suitable for importing into your favorite
accounting system.
"""

import itertools
import os
import copy
import decimal
import datetime
from textwrap import dedent

import autocommand
import ofxparse

import csv


def header(ofx):
	for field, value in ofx.headers.items():
		yield f'{field}:{value}'
	yield dedent(f"""
		<OFX>
		<SIGNONMSGSRSV1>
		<SONRS>
		<STATUS>
		<CODE>{ofx.signon.code}</CODE>
		<SEVERITY>{ofx.signon.severity}</SEVERITY>
		</STATUS>
		<DTSERVER>{ofx.signon.dtserver}</DTSERVER>
		<LANGUAGE>{ofx.signon.language}</LANGUAGE>
		</SONRS>
		</SIGNONMSGSRSV1>
		""").strip()
	yield dedent(f"""
		<INVSTMTMSGSRSV1>
		<INVSTMTTRNRS>
		<TRNUID>1</TRNUID>
		<STATUS>
		<CODE>0</CODE>
		<SEVERITY>INFO</SEVERITY>
		</STATUS>
		<INVSTMTRS>
		<DTASOF>{datetime.date.today().strftime("%Y%m%d")}</DTASOF>
		<CURDEF>{ofx.account.statement.currency}</CURDEF>
		<INVACCTFROM>
		<BROKERID>{ofx.account.brokerid}</BROKERID>
		<ACCTID>{ofx.account.account_id}</ACCTID>
		</INVACCTFROM>
		<INVTRANLIST>
		<DTSTART>{ofx.account.statement.start_date.strftime("%Y%m%d")}</DTSTART>
		<DTEND>{ofx.account.statement.end_date.strftime("%Y%m%d")}</DTEND>
		""").strip()


tmpl = dedent("""
	<{type}MF>
	<INV{type}>
	<INVTRAN>
	<FITID>{abs_amount}{abs_shares}{price:0.6f}{row[Date]}</FITID>
	<DTTRADE>{ofx_date}</DTTRADE>
	<MEMO>{row[Transaction]}</MEMO>
	</INVTRAN>
	<SECID>
	<UNIQUEID>{security.uniqueid}</UNIQUEID>
	<UNIQUEIDTYPE>CUSIP</UNIQUEIDTYPE>
	</SECID>
	<UNITS>{abs_shares}</UNITS>
	<UNITPRICE>{row[Price]}</UNITPRICE>
	<TOTAL>{row[Amount]}</TOTAL>
	<CURRENCY>
	<CURRATE>1.0000</CURRATE>
	<CURSYM>USD</CURSYM>
	</CURRENCY>
	<SUBACCTSEC>OTHER</SUBACCTSEC>
	<SUBACCTFUND>OTHER</SUBACCTFUND>
	</INV{type}>
	<{type}TYPE>{type}</{type}TYPE>
	</{type}MF>""").strip()


def to_ofx(row, securities):
	if row['Shares'] == 'N/A':
		return
	amount = decimal.Decimal(row['Amount'])
	price = decimal.Decimal(row['Price'])
	shares = decimal.Decimal(row['Shares'])
	type = 'SELL' if shares < 0 else 'BUY'
	abs_amount = abs(amount)
	abs_shares = abs(shares)
	date = datetime.datetime.strptime(row['Date'], '%m/%d/%Y').date()
	ofx_date = date.strftime('%Y%m%d')
	security = securities[row['Ticker']]

	yield tmpl.format_map(locals())


def footer(ofx):
	"""
	Given the original OFX template, extract the securities list.
	"""
	yield dedent(f"""
		</INVTRANLIST>
		</INVSTMTRS>
		</INVSTMTTRNRS>
		</INVSTMTMSGSRSV1>
		<SECLISTMSGSRSV1>
		<SECLIST>""").strip()
	for sec in ofx.security_list:
		yield dedent(f"""
			<MFINFO>
			<SECINFO>
			<SECID>
			<UNIQUEID>{sec.uniqueid}</UNIQUEID>
			<UNIQUEIDTYPE>CUSIP</UNIQUEIDTYPE>
			</SECID>
			<SECNAME>{sec.name}</SECNAME>
			<TICKER>{sec.ticker}</TICKER>
			</SECINFO>
			</MFINFO>
			""").strip()
	yield dedent(f"""
		</SECLIST>
		</SECLISTMSGSRSV1>
		</OFX>
		""").strip()


@autocommand.autocommand(__name__)
def main(csv_filename, ofx_filename, limit: int=None):
	"""
	Create a new OFX file based on the CSV and OFX downloads from
	PayChex.
	"""
	csv_filename = os.path.expanduser(csv_filename)
	ofx_filename = os.path.expanduser(ofx_filename)
	ofx = ofxparse.OfxParser.parse(open(ofx_filename))
	for line in header(ofx):
		print(line)
	dialect = copy.copy(csv.excel)
	dialect.skipinitialspace = True
	data = csv.DictReader(open(csv_filename), dialect=dialect)

	securities = {
		security.ticker: security
		for security in ofx.security_list
	}

	for row in itertools.islice(data, limit):
		for line in to_ofx(row, securities):
			print(line)

	for line in footer(ofx):
		print(line)
