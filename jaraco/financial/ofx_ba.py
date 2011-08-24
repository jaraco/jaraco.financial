#!/usr/bin/python
import time
import os
import httplib
import urllib2
import uuid
import sys
import argparse
import getpass
import itertools

from jaraco.util.string import local_format as lf

sites = {
	"SLFCU": {
		"caps": ["SIGNON", "BASTMT"],
		"fid": "1001",
		"fiorg": "SLFCU",
		"url": "https://www.cu-athome.org/scripts/serverext.dll",
		"bankid": "307083911",
	},
}

def _field(tag, value):
	return lf('<{tag}>{value}')

def _tag(tag, *contents):
	start_tag = lf('<{tag}>')
	end_tag = lf('</{tag}>')
	lines = itertools.chain([start_tag], contents, [end_tag])
	return '\r\n'.join(lines)

def _date():
	return time.strftime("%Y%m%d%H%M%S", time.localtime())

def _genuuid():
	return uuid.uuid4().hex

class OFXClient:
	"""Encapsulate an ofx client, config is a dict containg configuration"""
	def __init__(self, config, user, password):
		self.password = password
		self.user = user
		self.config = config
		self.cookie = 3
		config["user"] = user
		config["password"] = password
		if not config.has_key("appid"):
			config["appid"] = "QWIN"  # i've had to fake Quicken to actually get my unwilling test server to talk to me
			config["appver"] = "1200"

	def _cookie(self):
		self.cookie += 1
		return str(self.cookie)

	"""Generate signon message"""
	def _signOn(self):
		config = self.config
		fidata = [_field("ORG", config["fiorg"])]
		if config.has_key("fid"):
			fidata += [_field("FID", config["fid"])]
		return _tag("SIGNONMSGSRQV1",
			_tag("SONRQ",
				_field("DTCLIENT",_date()),
				_field("USERID",config["user"]),
				_field("USERPASS",config["password"]),
				_field("LANGUAGE","ENG"),
				_tag("FI", *fidata),
				_field("APPID",config["appid"]),
				_field("APPVER",config["appver"]),
			),
		)

	def _acctreq(self, dtstart):
		req = _tag("ACCTINFORQ", _field("DTACCTUP", dtstart))
		return self._message("SIGNUP", "ACCTINFO", req)

	# this is from _ccreq below and reading page 176 of the latest OFX doc.
	def _bareq(self, acctid, dtstart, accttype):
		config=self.config
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

	def _ccreq(self, acctid, dtstart):
		config=self.config
		req = _tag("CCSTMTRQ",
			_tag("CCACCTFROM", _field("ACCTID", acctid)),
			_tag("INCTRAN",
				_field("DTSTART", dtstart),
				_field("INCLUDE", "Y"),
			),
		)
		return self._message("CREDITCARD", "CCSTMT", req)

	def _invstreq(self, brokerid, acctid, dtstart):
		dtnow = time.strftime("%Y%m%d%H%M%S", time.localtime())
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
		config = self.config
		return _tag(msgType + "MSGSRQV1",
			_tag(trnType + "TRNRQ",
				_field("TRNUID", _genuuid()),
				_field("CLTCOOKIE", self._cookie()),
				request,
			),
		)

	def _header(self):
		return join("\r\n", [
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

	def baQuery(self, acctid, dtstart, accttype):
		"""Bank account statement request"""
		return join("\r\n",[
			self._header(),
			_tag("OFX",
				self._signOn(),
				self._bareq(acctid, dtstart, accttype),
			),
		])

	def ccQuery(self, acctid, dtstart):
		"""CC Statement request"""
		return join("\r\n",[
			self._header(),
			_tag("OFX",
				self._signOn(),
				self._ccreq(acctid, dtstart),
			),
		])

	def acctQuery(self,dtstart):
		return join("\r\n",[
			self._header(),
			_tag("OFX",
				self._signOn(),
				self._acctreq(dtstart),
			),
		])

	def invstQuery(self, brokerid, acctid, dtstart):
		return join("\r\n",[
			self._header(),
			_tag("OFX",
				self._signOn(),
				self._invstreq(brokerid, acctid,dtstart),
			),
		])

	def doQuery(self,query,name):
		# N.B. urllib doesn't honor user Content-type, use urllib2
		request = urllib2.Request(
			self.config["url"],
			query,
			{
				"Content-type": "application/x-ofx",
				"Accept": "*/*, application/x-ofx"
			},
		)
		if 1:
			f = urllib2.urlopen(request)
			response = f.read()
			f.close()

			f = file(name, "w")
			f.write(response)
			f.close()
		else:
			print request
			print self.config["url"], query

def get_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('site', help="One of {0}".format(', '.join(sites)))
	parser.add_argument('-u', '--username', default=getpass.getuser())
	parser.add_argument('-a', '--account')
	parser.add_argument('-t', '--account-type',
		help="Required if retrieving bank statement, should be CHECKING, SAVINGS, ...",
	)
	globals().update(args = parser.parse_args())

def handle_command_line():
	get_args()
	dtstart = time.strftime("%Y%m%d",time.localtime(time.time()-31*86400))
	dtnow = time.strftime("%Y%m%d",time.localtime())
	passwd = getpass.getpass()
	client = OFXClient(sites[args.site], args.username, passwd)
	if not args.account:
		query = client.acctQuery("19700101000000")
		client.doQuery(query, args.site+"_acct.ofx")
	else:
		caps = sites[args.site]['caps']
		if "CCSTMT" in caps:
			query = client.ccQuery(args.account, dtstart)
		elif "INVSTMT" in caps:
			query = client.invstQuery(sites[args.site]["fiorg"],
				args.account, dtstart)
		elif "BASTMT" in caps:
			query = client.baQuery(args.account, dtstart, args.account_type)
		client.doQuery(query, args.site+dtnow+".ofx")

if __name__=="__main__":
	handle_command_line()

