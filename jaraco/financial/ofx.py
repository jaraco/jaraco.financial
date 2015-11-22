from __future__ import absolute_import, unicode_literals, print_function

import uuid
import argparse
import getpass
import itertools
import collections
import datetime
import logging
import inspect
import json
import re
import warnings

import requests
import path
import dateutil.parser
import keyring
import pkg_resources
import ofxparse
import jaraco.collections
from jaraco.ui import cmdline
from jaraco.text import local_format as lf
import jaraco.logging
from requests.packages.urllib3.connectionpool import HTTPConnection

try:
	import yaml
except ImportError:
	pass

from . import msmoney

log = logging.getLogger(__name__)

sites = dict()


def disable_future_warning():
	"""
	Suppress warning as reported at
	https://github.com/jseutter/ofxparse/issues/87
	"""
	warnings.filterwarnings(
		action="ignore",
		category=FutureWarning,
		message="split\(\) requires a non-empty pattern match",
	)
disable_future_warning()


def load_sites():
	_load_sites_from_entry_points()
	_load_sites_from_file()

def _load_sites_from_entry_points():
	"""
	Locate all setuptools entry points by the name 'financial_institutions'
	and initialize them.
	Any third-party library may register an entry point by adding the
	following to their setup.py::

		entry_points = {
			'financial_institutions': {
				'institution set=mylib.mymodule:institutions',
			},
		},

	Where `institutions` is a dictionary mapping institution name to
	institution details.
	"""

	group = 'financial_institutions'
	entry_points = pkg_resources.iter_entry_points(group=group)
	for ep in entry_points:
		try:
			log.info('Loading %s', ep.name)
			detail = ep.load()
			sites.update(detail)
		except Exception:
			log.exception("Error initializing institution %s." % ep)

def _load_sites_from_file():
	if 'yaml' not in globals():
		return
	sites_file = path.path('~/Documents/Financial/institutions.yaml')
	sites_file = sites_file.expanduser()
	if not sites_file.exists():
		return
	with sites_file.open() as stream:
		new_sites = yaml.safe_load(stream)
	sites.update(new_sites)

def _field(tag, value):
	return lf('<{tag}>{value}')

def _tag(tag, *contents):
	start_tag = lf('<{tag}>')
	end_tag = lf('</{tag}>')
	lines = itertools.chain([start_tag], contents, [end_tag])
	return '\r\n'.join(lines)

def _date():
	return datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")

def _genuuid():
	return uuid.uuid4().hex

AppInfo = collections.namedtuple('AppInfo', 'id version')

def handle_response(resp):
	"""
	handle a requests Response
	"""
	if not resp.ok:
		with open('err.txt', 'wb') as err_f:
			err_f.write(resp.content)
	resp.raise_for_status()

def sign_on_message(config):
	fidata = [_field("ORG", config["fiorg"])]
	if 'fid' in config:
		fidata += [_field("FID", config["fid"])]
	return _tag(
		"SIGNONMSGSRQV1",
		_tag(
			"SONRQ",
			_field("DTCLIENT", _date()),
			_field("USERID", config["user"]),
			_field("USERPASS", config["password"]),
			_field("LANGUAGE", "ENG"),
			_tag("FI", *fidata),
			_field("APPID", config["appid"]),
			_field("APPVER", config["appver"]),
		),
	)

def get_version_id():
	"""
	OFX seems to like version ids that look like NNNN, so generate something
	like that from our version.
	"""
	ver = pkg_resources.require('jaraco.financial')[0].version
	ver_id = ''.join(re.findall('\d+', ver))
	# first pad right to three digits (so last two digits are minor/patch ver)
	ver_id = '{:0<3s}'.format(ver_id)
	# now pad left to four digits (so first two digits are major ver)
	ver_id = '{:0>4s}'.format(ver_id)
	assert len(ver_id) == 4
	return ver_id

class OFXClient(object):
	"""
	Encapsulate an ofx client, config is a dict containing configuration.
	"""

	# pyofx is appears to be work for many institutions
	pyofx = AppInfo('PyOFX', '0100')
	# if you have problems, fake quicken with one of these app ids
	quicken_2009 = AppInfo('QWIN', '1800')
	quicken_older = AppInfo('QWIN', '1200')
	money_sunset = AppInfo('Money Plus', '1700')

	app = pyofx
	session = requests.Session()

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

	def sign_on(self):
		"""Generate signon message"""
		return sign_on_message(self.config)

	def _acctreq(self, dtstart):
		req = _tag("ACCTINFORQ", _field("DTACCTUP", dtstart))
		return self._message("SIGNUP", "ACCTINFO", req)

	# this is from _ccreq below and reading page 176 of the latest OFX doc.
	def _bareq(self, bankid, acctid, dtstart, accttype):
		req = _tag("STMTRQ",
			_tag(
				"BANKACCTFROM",
				_field("BANKID", bankid),
				_field("ACCTID", acctid),
				_field("ACCTTYPE", accttype),
			),
			_tag(
				"INCTRAN",
				_field("DTSTART", dtstart),
				_field("INCLUDE", "Y"),
			),
		)
		return self._message("BANK", "STMT", req)

	def _ccreq(self, acctid, dtstart):
		req = _tag(
			"CCSTMTRQ",
			_tag(
				"CCACCTFROM", _field("ACCTID", acctid)),
			_tag(
				"INCTRAN",
				_field("DTSTART", dtstart),
				_field("INCLUDE", "Y"),
			),
		)
		return self._message("CREDITCARD", "CCSTMT", req)

	def _invstreq(self, brokerid, acctid, dtstart):
		dtnow = _date()
		req = _tag(
				"INVSTMTRQ",
			_tag(
				"INVACCTFROM",
				_field("BROKERID", brokerid),
				_field("ACCTID", acctid),
			),
			_tag(
				"INCTRAN",
				_field("DTSTART", dtstart),
				_field("INCLUDE", "Y"),
			),
			_field("INCOO", "Y"),
			_tag(
				"INCPOS",
				_field("DTASOF", dtnow),
				_field("INCLUDE", "Y"),
			),
			_field("INCBAL", "Y"),
		)
		return self._message("INVSTMT", "INVSTMT", req)

	def _message(self, msgType, trnType, request):
		return _tag(msgType + "MSGSRQV1",
			_tag(
				trnType + "TRNRQ",
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

	def baQuery(self, bankid, acctid, dtstart, accttype):
		"""Bank account statement request"""
		return '\r\n'.join([
			self._header(),
			_tag(
				"OFX",
				self.sign_on(),
				self._bareq(bankid, acctid, dtstart, accttype),
			),
		])

	def ccQuery(self, acctid, dtstart):
		"""CC Statement request"""
		return '\r\n'.join([
			self._header(),
			_tag(
				"OFX",
				self.sign_on(),
				self._ccreq(acctid, dtstart),
			),
		])

	def acctQuery(self, dtstart):
		return '\r\n'.join([
			self._header(),
			_tag(
				"OFX",
				self.sign_on(),
				self._acctreq(dtstart),
			),
		])

	def invstQuery(self, brokerid, acctid, dtstart):
		return '\r\n'.join([
			self._header(),
			_tag(
				"OFX",
				self.sign_on(),
				self._invstreq(brokerid, acctid, dtstart),
			),
		])

	def doQuery(self, query, name):
		headers = {
			"Content-type": "application/x-ofx",
			"Accept": "*/*, application/x-ofx",
		}

		resp = self.session.post(
			url=self.config["url"],
			data=query.encode('cp1252'),
			headers=headers,
		)

		handle_response(resp)

		content_type = resp.headers['Content-type']
		expected_types = 'application/x-ofx', 'application/qfx'
		if content_type not in expected_types:
			log.warning(lf('Unexpected content type {content_type}'))

		with open(name, "wb") as outfile:
			outfile.write(resp.content)


class Account(dict, jaraco.collections.ItemsAsAttributes):
	@property
	def username(self):
		return self.get('username', getpass.getuser())

	def __str__(self):
		return '{institution} ({account})'.format(**self)

	def matches(self, query):
		return query.lower() in self.institution.lower()


class DateAction(argparse.Action):
	def __call__(self, parser, namespace, values, option_string=None):
		value = values
		value = dateutil.parser.parse(value)
		setattr(namespace, self.dest, value)

class Command(cmdline.Command):
	@staticmethod
	def download(site, account, dt_start, creds, account_type=None):
		config = sites[site]
		client = OFXClient(config, *creds)

		caps = sites[site]['caps']
		if "CCSTMT" in caps:
			query = client.ccQuery(account, dt_start)
		elif "INVSTMT" in caps:
			query = client.invstQuery(sites[site]["fiorg"], account, dt_start)
		elif "BASTMT" in caps:
			bank_id = config["bankid"]
			query = client.baQuery(bank_id, account, dt_start, account_type)
		filename = '{site} {account} {dtnow}.ofx'.format(
			dtnow = datetime.datetime.now().strftime('%Y-%m-%d'),
			**vars())
		filename = path.path(filename)
		client.doQuery(query, filename)
		return filename

	@staticmethod
	def _get_password(site, username):
		password = keyring.get_password(site, username)
		if password is None:
			password = getpass.getpass(lf("Password for {site}:{username}: "))
			keyring.set_password(site, username, password)
		return password


class Query(Command):
	@classmethod
	def add_arguments(cls, parser):
		parser.add_argument('site', help="One of {0}".format(', '.join(sites)))
		parser.add_argument('-u', '--username', default=getpass.getuser())
		parser.add_argument('-a', '--account')
		parser.add_argument(
			'-t', '--account-type',
			help="Required if retrieving bank statement, should be CHECKING, "
				"SAVINGS, ...",
		)
		default_start = datetime.datetime.now() - datetime.timedelta(days=31)
		parser.add_argument('-d', '--start-date', default=default_start,
			action=DateAction)

	@classmethod
	def run(cls, args):
		creds = args.username, cls._get_password(args.site, args.username)
		if not args.account:
			# download account info
			config = sites[args.site]
			client = OFXClient(config, *creds)
			query = client.acctQuery("19700101000000")
			client.doQuery(query, args.site + "_acct.ofx")
		else:
			dt_start = args.start_date.strftime("%Y%m%d")
			cls.download(args.site, args.account, dt_start, creds,
				args.account_type)


class Base:
	root = path.path('~/Documents/Financial').expanduser()


class Accounts(Base):
	@classmethod
	def load_accounts(cls):
		docs = cls.load_accounts_yaml() or cls.load_accounts_json()
		return list(map(Account, docs))

	@classmethod
	def load_accounts_yaml(cls):
		"""
		Preferred mechanism for defining accounts.
		"""
		accounts = cls.root / 'accounts.yaml'
		if not accounts.exists() or 'yaml' not in globals():
			return
		with accounts.open() as stream:
			return yaml.safe_load(stream)

	@classmethod
	def load_accounts_json(cls):
		"backward-compatible JSON-based account definition"
		accounts = cls.root / 'accounts.json'
		with accounts.open() as stream:
			warnings.warn("JSON account definition is deprecated",
				DeprecationWarning)
			return json.load(stream)

	@classmethod
	def best_account(cls, input):
		return next(
			account
			for account in cls.load_accounts()
			if input in account.institution
		)

	@classmethod
	def matching_accounts(cls, query):
		return [
			account for account in cls.load_accounts()
			if account.matches(query)
		]


class DownloadAll(Accounts, Command):
	@classmethod
	def add_arguments(cls, parser):
		default_start = datetime.datetime.now() - datetime.timedelta(days=31)
		parser.add_argument('-d', '--start-date', default=default_start,
			action=DateAction)
		parser.add_argument('-v', '--validate', default=False,
			action="store_true")
		parser.add_argument('-l', '--launch', default=False,
			action="store_true", help="Launch the downloaded file in MS "
				"Money (implies validate).")
		parser.add_argument('-k', '--like', help="Only download the accounts "
			"whose names are like the supplied string.",
			default=cls.load_accounts(), type=cls.matching_accounts,
			dest='accounts')

	@classmethod
	def run(cls, args):
		print('Matching {}/{} accounts'.format(
			len(args.accounts),
			len(cls.load_accounts())))
		for account in args.accounts:
			log.info('Downloading %(institution)s (%(account)s)' % account)
			username = account.get('username', getpass.getuser())
			site = account['institution']
			creds = username, cls._get_password(site, username)
			acct_type = account.get('type', '').upper() or None
			dt_start = args.start_date.strftime("%Y%m%d")
			ofx = cls.download(site, account['account'], dt_start, creds,
				acct_type)
			if args.validate or args.launch:
				cls.validate(ofx)
			if args.launch:
				msmoney.launch(ofx)
				ofx.remove()

	@classmethod
	def validate(cls, ofx_file):
		parser = ofxparse.OfxParser()
		with open(ofx_file, 'rb') as reader:
			doc = parser.parse(reader)
		assert doc.account.statement


class ListInstitutions(Command):
	@classmethod
	def run(cls, args):
		list(map(print, sites))


class UpdatePassword(Accounts, Command):
	@classmethod
	def add_arguments(cls, parser):
		parser.add_argument('account', type=cls.best_account)

	@classmethod
	def run(cls, args):
		prompt = "password for {account}> ".format(**vars(args))
		new_password = getpass.getpass(prompt)
		if not new_password:
			return
		keyring.set_password(args.account.institution, args.account.username,
			new_password)


def get_args():
	"""
	Parse command-line arguments, including the Command and its arguments.
	"""
	usage = inspect.getdoc(handle_command_line)
	parser = argparse.ArgumentParser(usage=usage)
	jaraco.logging.add_arguments(parser)
	Command.add_subparsers(parser)
	return parser.parse_args()

def setup_requests_logging(level):
	requests_log = logging.getLogger("requests.packages.urllib3")
	requests_log.setLevel(level)
	requests_log.propagate = True

	# enable debugging at httplib level
	HTTPConnection.debuglevel = level <= logging.DEBUG

def handle_command_line():
	args = get_args()
	jaraco.logging.setup(args, format="%(message)s")
	setup_requests_logging(args.log_level)
	load_sites()
	args.action.run(args)

if __name__ == "__main__":
	handle_command_line()
