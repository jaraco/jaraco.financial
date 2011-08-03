
import datetime
now = datetime.datetime.now

from persistent import Persistent

import db
_db = db.GetDatabase()

class Entry( Persistent ):
	"""This is a 'side' of a transaction.  It is an expense, an income, or
	In the case of double-entry accounting,
	this is a single entry.
	An expense is a negative amount with the source account being where the
	money coming from and the recipient is the payee.
	A transfer can consist of one or two entries.  It should use 1 entry
	when the transfer happens transactionally.  There
	should be two if there is a time shift between occurrances.
	A split transaction or paycheck will use a ledger to collect the
	transactions.  So a paycheck, for example, would consist of one Entry
	of gross pay - donor is employer - destination account is a ledger for
	this paycheck.  As taxes are withdrawn, each tax would be another
	Entry with the source account being the ledger and the recipient being
	the tax agency."""
	def __init__( self ):
		self.time_entered = now()

	def validate( self ):
		assert hasattr( self, 'recipient' ) or hasattr( self, 'donor' )
		assert hasattr( self, 'source' ) or hasattr( self, 'destination' )
		assert hasattr( self, 'amount' ) is not None
		if hasattr( self, 'amount' ) == 0: self.warn( 'amount is zero' )
		
	def warn( self, msg ):
		print 'warning:', msg

	more_doc = """
		time = now()
	amount = 0
	category = ( food, )
	subcategory = ( diningout, )
	activity = ( real estate, inicom, sandia )
	specific to = ( 1005 carol, china project, ... )
	recipient, donor
	activities*
	source, destination
"""

"todo: address currencies and investments"
class Ledger( Persistent ):
	"This is a collection of Entries that should be grouped" 
	description = 'finincial exchange'
	def GetAmount( self ):
		"Return the sum total of the ledger"

	def GetDateRange( self ):
		"Return the date range covered by this ledger"

class Account( Ledger ):
	"A first-class account"

class Entity( Persistent ):
	"A person, company, etc., capable of receiving or sourcing funds"
