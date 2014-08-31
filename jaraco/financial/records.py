import os
import subprocess
import smtplib
import email.mime.multipart
import email.mime.text
import getpass

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

def hash_files(root):
	proc = subprocess.Popen(['fciv', '-add', root, '-bp', root, '-r'],
		stdout=subprocess.PIPE)
	output, error = proc.communicate()
	if os.path.isfile('fciv.err'):
		os.remove('fciv.err')
	return output.decode('utf-8')

def send_hashes():
	"""
	Hash the files in ~/Documents
	and send the hashes through a notary service to serve as
	evidence of existence of the versions of the files
	available today.
	"""
	root = os.path.expanduser('~/Documents')
	output = hash_files(root)
	email_message(output, "Document Hashes")
