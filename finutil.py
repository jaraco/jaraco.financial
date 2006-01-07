# financial tools
import codecs
import string
from itertools import *
import sets

f = codecs.open( r'c:\documents and settings\jaraco\desktop\book1.txt', 'rb', encoding='utf-16' )
#r = csv.reader( f, dialect='excel-tab' )
# csv reader can't handle unicode strings (bastards)
fixed = imap( lambda s: s.split( '\t' ), imap( lambda s: s.strip( '\r\n' ), f ) )
header = fixed.next()
transactions = list( fixed )
columns = zip( *transactions )
accounts = sets.Set( columns[2] )
payees = sets.Set( columns[3] )

