import ZODB.config
db = ZODB.config.databaseFromURL('summs.conf')
conn = db.open()
dbroot = conn.root()
from BTrees.OOBTree import OOBTree
dbname = 'summs'
dbroot[dbname] = OOBTree()
mondb = dbroot[dbname]
from persistent import Persistent
class ServiceTable(Persistent):
	def __init__(self):
		self.id = ''
		self.name = ''
		self.description = ''
		self.service = ''
		self.hostname = ''
		self.state_current = ''
		self.state_last = ''
		self.time_lastcheck = ''
		self.time_lastok = ''
		self.time_lastwarn = ''
		self.time_lasterror = ''

newmon = ServiceTable()
newmon.id = 'myserver.hostingcompany.com-httpd' 
newmon.name = 'Apache Web Server'
newmon.description = 'This is the staging Web Server Service for 16 low-volume clients'
newmon.service = 'httpd'
newmon.hostname = 'myserver'
newmon.state_current = 'OK'
newmon.state_last = 'OK'
mondb[newmon.id] = newmon
import transaction
transaction.get().commit()
