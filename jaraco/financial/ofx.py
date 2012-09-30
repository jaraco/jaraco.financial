from __future__ import absolute_import, unicode_literals, print_function

import urllib2
import uuid
import argparse
import getpass
import itertools
import collections
import datetime
import contextlib
import logging
import inspect
import json

import path
import dateutil.parser
import keyring
import jaraco.util.string as jstring
from jaraco.util.string import local_format as lf
import jaraco.util.logging
import jaraco.util.meta

log = logging.getLogger(__name__)

def load_sites():
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

	try:
		import pkg_resources
	except ImportError:
		log.warning('setuptools not available - entry points cannot be '
			'loaded')
		return

	group = 'financial_institutions'
	entry_points = pkg_resources.iter_entry_points(group=group)
	for ep in entry_points:
		try:
			log.info('Loading %s', ep.name)
			detail = ep.load()
			sites.update(detail)
		except Exception:
			log.exception("Error initializing institution %s." % ep)

sites = dict()

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

def sign_on_message(config):
	fidata = [_field("ORG", config["fiorg"])]
	if 'fid' in config:
		fidata += [_field("FID", config["fid"])]
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

	def sign_on(self):
		"""Generate signon message"""
		return sign_on_message(self.config)

	def _acctreq(self, dtstart):
		req = _tag("ACCTINFORQ", _field("DTACCTUP", dtstart))
		return self._message("SIGNUP", "ACCTINFO", req)

	# this is from _ccreq below and reading page 176 of the latest OFX doc.
	def _bareq(self, bankid, acctid, dtstart, accttype):
		req = _tag("STMTRQ",
			_tag("BANKACCTFROM",
				_field("BANKID", bankid),
				_field("ACCTID", acctid),
				_field("ACCTTYPE", accttype),
			),
			_tag("INCTRAN",
				_field("DTSTART", dtstart),
				_field("INCLUDE", "Y"),
			),
		)
		return self._message("BANK", "STMT", req)

	def _ccreq(self, acctid, dtstart):
		req = _tag("CCSTMTRQ",
			_tag("CCACCTFROM", _field("ACCTID", acctid)),
			_tag("INCTRAN",
				_field("DTSTART", dtstart),
				_field("INCLUDE", "Y"),
			),
		)
		return self._message("CREDITCARD", "CCSTMT", req)

	def _invstreq(self, brokerid, acctid, dtstart):
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
		return self._message("INVSTMT", "INVSTMT", req)

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

	def baQuery(self, bankid, acctid, dtstart, accttype):
		"""Bank account statement request"""
		return '\r\n'.join([
			self._header(),
			_tag("OFX",
				self.sign_on(),
				self._bareq(bankid, acctid, dtstart, accttype),
			),
		])

	def ccQuery(self, acctid, dtstart):
		"""CC Statement request"""
		return '\r\n'.join([
			self._header(),
			_tag("OFX",
				self.sign_on(),
				self._ccreq(acctid, dtstart),
			),
		])

	def acctQuery(self, dtstart):
		return '\r\n'.join([
			self._header(),
			_tag("OFX",
				self.sign_on(),
				self._acctreq(dtstart),
			),
		])

	def invstQuery(self, brokerid, acctid, dtstart):
		return '\r\n'.join([
			self._header(),
			_tag("OFX",
				self.sign_on(),
				self._invstreq(brokerid, acctid, dtstart),
			),
		])

	def doQuery(self, query, name):
		headers = {
			"Content-type": "application/x-ofx",
			"Accept": "*/*, application/x-ofx",
		}
		request = urllib2.Request(
			self.config["url"],
			data = query,
			headers = headers,
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

# todo: move the following class to jaraco.util
class Command(object):
	__metaclass__ = jaraco.util.meta.LeafClassesMeta

	@classmethod
	def add_subparsers(cls, parser):
		subparsers = parser.add_subparsers()
		[cmd_class.add_parser(subparsers) for cmd_class in cls._leaf_classes]

	@classmethod
	def add_parser(cls, subparsers):
		cmd_string = jstring.words(cls.__name__).lowered().dash_separated()
		parser = subparsers.add_parser(cmd_string)
		parser.set_defaults(action=cls)
		return parser

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
		client.doQuery(query, filename)

	@staticmethod
	def _get_password(site, username):
		password = keyring.get_password(site, username)
		if password is None:
			password = getpass.getpass(lf("Password for {site}:{username}: "))
			keyring.set_password(site, username, password)
		return password


class Query(Command):
	@classmethod
	def add_parser(cls, subparsers):
		parser = super(Query, cls).add_parser(subparsers)
		parser.add_argument('site', help="One of {0}".format(', '.join(sites)))
		parser.add_argument('-u', '--username', default=getpass.getuser())
		parser.add_argument('-a', '--account')
		parser.add_argument('-t', '--account-type',
			help="Required if retrieving bank statement, should be CHECKING, SAVINGS, ...",
		)
		default_start = datetime.datetime.now() - datetime.timedelta(days=31)
		parser.add_argument('-d', '--start-date', default=default_start,
			action=DateAction)
		return parser

	@classmethod
	def run(cls):
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

class DownloadAll(Command):
	@classmethod
	def add_parser(cls, subparsers):
		parser = super(DownloadAll, cls).add_parser(subparsers)
		default_start = datetime.datetime.now() - datetime.timedelta(days=31)
		parser.add_argument('-d', '--start-date', default=default_start,
			action=DateAction)
		return parser

	@classmethod
	def run(cls):
		root = path.path('~/Documents/Financial').expanduser()
		accounts = root / 'accounts.json'
		with open(accounts) as f:
			accounts = json.load(f)
		print('Found', len(accounts), 'accounts')
		for account in accounts:
			log.info('Downloading %(institution)s' % account)
			username = account.get('username', getpass.getuser())
			site = account['institution']
			creds = username, cls._get_password(site, username)
			acct_type = account.get('type', '').upper() or None
			dt_start = args.start_date.strftime("%Y%m%d")
			cls.download(site, account['account'], dt_start, creds, acct_type)

def get_args():
	"""
	Parse command-line arguments, including the Command and its arguments.
	"""
	usage = inspect.getdoc(handle_command_line)
	parser = argparse.ArgumentParser(usage=usage)
	jaraco.util.logging.add_arguments(parser)
	Command.add_subparsers(parser)
	args = parser.parse_args()
	globals().update(args = args)
	return args

def handle_command_line():
	args = get_args()
	jaraco.util.logging.setup(args)
	load_sites()
	args.action.run()

args = None
if __name__ == "__main__":
	handle_command_line()
