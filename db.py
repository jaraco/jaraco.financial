from ZODB import FileStorage, DB
import ZODB.config
import ZEO.ClientStorage
import os, operator
import transaction

from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet

current = os.path.dirname( __file__ )

def GetDatabase( ):
	"""Get the summs database.  Uses summs.conf in the current directory.  DB will be created
	if it doesn't exist."""
	#root = os.path.join( os.environ['APPDATA'], 'jaraco', 'SUMMS' )
	#if not os.path.isdir( root ): os.makedirs( root )
	conf = os.path.join( current, 'summs.conf' )
	db = ZODB.config.databaseFromURL( conf )
	conn = db.open()
	dbroot = conn.root()
	dbname = 'summs'
	summsdb = dbroot.setdefault( dbname, OOBTree() )
	return summsdb

from importer import *
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
import datetime

def ImportMoney():
	"This function currently requires an excel spreadsheet of the Money data"
	i = MoneyImporter( default )
	imported = summsdb.setdefault( 'imported', OOBTree() )
	now = datetime.datetime.now()
	target = imported.setdefault( now, PersistentList() )
	i.GetRows()
	pRows = itertools.imap( PersistentMapping, i.rows )
	target.extend( pRows )
	transaction.commit()

# gen purpose
def CreateSet( target_ob, target_name, orig_set, attr_name ):
	"""Take an attribute from the original set of items and create
	a set in the target object called target_name that contains
	unique copies of the attribute from the original set.
	e.g. CreateSet( summsdb, 'Categories', LatestImport(), 'Category' )"""
	set = OOSet()
	orig_set = itertools.ifilter( lambda o: attr_name in o, orig_set )
	items = itertools.imap( operator.itemgetter( attr_name ), orig_set )
	ExtendSet( set, items )
	target_ob[ target_name ] = set

def ExtendSet( set, items ):
	map( set.insert, items )

def LatestImport( ):
	return summsdb['imported'][ summsdb['imported'].maxKey() ]

def CleanNone( ob ):
	for item in ob:
		for key in item.keys():
			if item[key] is None:
				del item[key]
