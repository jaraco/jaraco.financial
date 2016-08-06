from __future__ import print_function

import smtplib
import email.mime.multipart
import email.mime.text
import getpass
import io
import codecs

from path import Path
from jaraco.ui import progress


def email_message(body_text, subject=None):
	SMTP_SERVER = 'pod51011.outlook.com'
	SMTP_PORT = 587
	SMTP_USERNAME = 'jaraco@jaraco.com'
	SMTP_PASSWORD = getpass.getpass()
	SMTP_FROM = 'jaraco@jaraco.com'
	SMTP_TO = 'jaraco@jaraco.com.readnotify.com'

	msg = email.mime.multipart.MIMEMultipart()
	body = email.mime.text.MIMEText(body_text)
	msg.attach(body)
	msg.add_header('From', SMTP_FROM)
	msg.add_header('To', SMTP_TO)
	if subject:
		msg.add_header('Subject', subject)

	# now send the message
	mailer = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
	mailer.starttls()
	try:
		mailer.login(SMTP_USERNAME, SMTP_PASSWORD)
	except NameError:
		pass
	mailer.sendmail(SMTP_FROM, [SMTP_TO], msg.as_string())
	mailer.close()

def _as_hex(bytes):
	"""
	Replacement for ``bytes.encode('hex')`` but on Python 3
	"""
	return codecs.encode(bytes, 'hex_codec').decode('ascii')

def hash_files(root):
	"""
	>>> res = hash_files(Path(__file__).dirname())
	Discovering documents
	Hashing documents
	...
	>>> print(res)
	d41d8cd98f00b204e9800998ecf8427e __init__.py
	...
	"""
	output = io.StringIO()
	print("Discovering documents")
	files = list(root.walkfiles())
	print("Hashing documents")
	bar = progress.TargetProgressBar(len(files))
	for path in bar.iterate(files):
		print(_as_hex(path.read_md5()), path.relpath(root), file=output)
	return output.getvalue()

def send_hashes():
	"""
	Hash the files in ~/Documents
	and send the hashes through a notary service to serve as
	evidence of existence of the versions of the files
	available today.
	"""
	root = Path('~/Documents').expanduser()
	output = hash_files(root)
	print("Sending hashes ({length} bytes)".format(length=len(output)))
	email_message(output, "Document Hashes")
