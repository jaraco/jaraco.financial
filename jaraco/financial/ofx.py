#!/usr/bin/python
import os
import httplib
import urllib2
import uuid
import sys
import argparse
import getpass
import itertools
import collections
import datetime
import contextlib
import logging

import dateutil.parser
import keyring
from jaraco.util.string import local_format as lf
import jaraco.util.logging

log = logging.getLogger(__name__)

sites = {
	"SLFCU": dict(
		caps = ["SIGNON", "BASTMT"],
		fid = "1001",
		fiorg = "SLFCU",
		url = "https://www.cu-athome.org/scripts/serverext.dll",
		bankid = "307083911",
	),
	"Chase (Credit Card)": dict(
		caps = ["SIGNON", "CCSTMT"],
		fid = "10898",
		fiorg = "B1",
		url = "https://ofx.chase.com",
	),
	"Los Alamos National Bank": dict(
		caps = ['SIGNON', 'BASTMT'],
		fid = '107001012',
		fiorg = 'LANB',
		url = 'https://www.lanb.com/ofx/ofxrelay.dll',
		bankid = '107001012',
	),
}

def _field(tag, value):
	return lf('<{tag}>{value}')

def _tag(tag, *contents):
	start_tag = lf('<{tag}>')
	end_tag = lf('</{tag}>')
	lines = itertools.chain([start_tag], contents, [end_tag])
	return '\r\n'.join(lines)

def _date():
	return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

def _genuuid():
	"""
	Generate a UUID as a string in hex format
	"""
	return uuid.uuid4().hex

AppInfo = collections.namedtuple('AppInfo', 'id version')

@contextlib.contextmanager
def url_context(*args, **kwargs):
	"""
	Context wrapper around urlopen
	"""
	response = urllib2.urlopen(*args, **kwargs)
	try:
		yield response
	finally:
		response.close()


class OFXClient(object):
	"""
	Encapsulate an ofx client, config is a dict containg configuration.
	"""

	# set up some app ids
	pyofx = AppInfo('PyOFX', '0100')
	# if you have problems, fake quicken with one of these app ids
	quicken_2009 = AppInfo('QWIN', '1800')
	quicken_older = AppInfo('QWIN', '1200')

	app = pyofx

	def __init__(self, config, user, password):
		self.password = password
		self.user = user
		self.config = config
		self.cookie = 3
		config["user"] = user
		config["password"] = password
		config.setdefault('appid', self.app.id)
		config.setdefault('appver', self.app.version)

	def _cookie(self):
		self.cookie += 1
		return str(self.cookie)

	def _sign_on(self):
		"""
		Generate the sign-on message
		"""
		config = self.config
		fidata = [_field("ORG", config["fiorg"])]
		if config.has_key("fid"):
			fidata.append(_field("FID", config["fid"]))
		return _tag("SIGNONMSGSRQV1",
			_tag("SONRQ",
				_field("DTCLIENT", _date()),
				_field("USERID", config["user"]),
				_field("USERPASS", config["password"]),
				_field("LANGUAGE", "ENG"),
				_tag("FI", *fidata),
				_field("APPID", config["appid"]),
				_field("APPVER", config["appver"]),
			),
		)

	def _account_request(self, dtstart):
		req = _tag("ACCTINFORQ", _field("DTACCTUP", dtstart))
		return self._message("SIGNUP", "ACCTINFO", req)

	def _bank_statement_request(self, acctid, dtstart, accttype):
		req = _tag("STMTRQ",
			_tag("BANKACCTFROM",
				_field("BANKID", sites[args.site]["bankid"]),
				_field("ACCTID", acctid),
				_field("ACCTTYPE", accttype),
			),
			_tag("INCTRAN",
				_field("DTSTART", dtstart),
				_field("INCLUDE", "Y"),
			),
		)
		return self._message("BANK", "STMT", req)

	def _credit_card_statement_request(self, acctid, dtstart):
		req = _tag("CCSTMTRQ",
			_tag("CCACCTFROM", _field("ACCTID", acctid)),
			_tag("INCTRAN",
				_field("DTSTART", dtstart),
				_field("INCLUDE", "Y"),
			),
		)
		return self._message("CREDITCARD", "CCSTMT", req)

	def _investment_request(self, brokerid, acctid, dtstart):
		dtnow = _date()
		req = _tag("INVSTMTRQ",
			_tag("INVACCTFROM",
				_field("BROKERID", brokerid),
				_field("ACCTID", acctid),
			),
			_tag("INCTRAN",
				_field("DTSTART", dtstart),
				_field("INCLUDE", "Y"),
			),
			_field("INCOO", "Y"),
			_tag("INCPOS",
				_field("DTASOF", dtnow),
				_field("INCLUDE", "Y"),
			),
			_field("INCBAL", "Y"),
		)
		return self._message("INVSTMT","INVSTMT",req)

	def _message(self, msgType, trnType, request):
		return _tag(msgType + "MSGSRQV1",
			_tag(trnType + "TRNRQ",
				_field("TRNUID", _genuuid()),
				_field("CLTCOOKIE", self._cookie()),
				request,
			),
		)

	def _header(self):
		return '\r\n'.join([
			"OFXHEADER:100",
			"DATA:OFXSGML",
			"VERSION:102",
			"SECURITY:NONE",
			"ENCODING:USASCII",
			"CHARSET:1252",
			"COMPRESSION:NONE",
			"OLDFILEUID:NONE",
			"NEWFILEUID:" + _genuuid(),
			"",
		])

	def bank_account_query(self, acctid, dtstart, accttype):
		"""Bank account statement request"""
		return '\r\n'.join([
			self._header(),
			_tag("OFX",
				self._sign_on(),
				self._bank_statement_request(acctid, dtstart, accttype),
			),
		])

	def credit_card_query(self, acctid, dtstart):
		"""CC Statement request"""
		return '\r\n'.join([
			self._header(),
			_tag("OFX",
				self._sign_on(),
				self._credit_card_statement_request(acctid, dtstart),
			),
		])

	def account_query(self,dtstart):
		return '\r\n'.join([
			self._header(),
			_tag("OFX",
				self._sign_on(),
				self._account_request(dtstart),
			),
		])

	def investment_query(self, brokerid, acctid, dtstart):
		return '\r\n'.join([
			self._header(),
			_tag("OFX",
				self._sign_on(),
				self._investment_request(brokerid, acctid,dtstart),
			),
		])

	def do_query(self, query, name):
		headers = {
			"Content-type": "application/x-ofx",
			"Accept": "*/*, application/x-ofx",
		}
		request = urllib2.Request(
			self.config["url"],
			query,
			headers,
		)

		url = self.config["url"]
		log.debug(lf("URL is {url}; query is {query}"))

		with url_context(request) as response:
			payload = response.read()
			content_type = response.headers.getheader('Content-type')
			if content_type != 'application/x-ofx':
				log.warning(lf('Unexpected content type {content_type}'))

		with file(name, "w") as outfile:
			outfile.write(payload)

class DateAction(argparse.Action):
	def __call__(self, parser, namespace, values, option_string=None):
		value = values
		value = dateutil.parser.parse(value)
		setattr(namespace, self.dest, value)

def get_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('site', help="One of {0}".format(', '.join(sites)))
	parser.add_argument('-u', '--username', default=getpass.getuser())
	parser.add_argument('-a', '--account')
	parser.add_argument('-t', '--account-type',
		help="Required if retrieving bank statement, should be CHECKING, SAVINGS, ...",
	)
	default_start = datetime.datetime.now() - datetime.timedelta(days=31)
	parser.add_argument('-d', '--start-date', default=default_start,
		action=DateAction)
	jaraco.util.logging.add_arguments(parser)
	globals().update(args = parser.parse_args())

def _get_password():
	site = args.site
	username = args.username
	password = keyring.get_password(site, username)
	if password is None:
		password = getpass.getpass(lf("Password for {site}:{username}: "))
		keyring.set_password(site, username, password)
	return password

def handle_command_line():
	get_args()
	jaraco.util.logging.setup(args)
	dtstart = args.start_date.strftime("%Y%m%d")
	now = datetime.datetime.now()
	dtnow = now.strftime('%Y-%m-%d')
	passwd = _get_password()
	client = OFXClient(sites[args.site], args.username, passwd)
	if not args.account:
		query = client.account_query("19700101000000")
		filename = "{args.site} account info.ofx".format(**globals())
	else:
		caps = sites[args.site]['caps']
		if "CCSTMT" in caps:
			query = client.credit_card_query(args.account, dtstart)
		elif "INVSTMT" in caps:
			query = client.investment_query(sites[args.site]["fiorg"],
				args.account, dtstart)
		elif "BASTMT" in caps:
			query = client.bank_account_query(args.account, dtstart,
				args.account_type)
		filename = '{args.site} {dtnow}.ofx'.format(args=args, dtnow=dtnow)
	client.do_query(query, filename)

if __name__=="__main__":
	handle_command_line()
