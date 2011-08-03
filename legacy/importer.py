from win32com.client import Dispatch
import itertools
import datetime

class MoneyImporter( object ):

	def __init__( self, filename ):	
		self.xlapp = Dispatch( 'Excel.Application' )
		self.wb = self.xlapp.Workbooks.Open( filename )
		self.ws = self.wb.Sheets[0]

	def GetRow( self, n ):
		return self.ws.Rows(n).Value[0]

	def FixDate( self, r ):	
		r['Date'] = datetime.date.fromtimestamp( int( r['Date'] ) )
		return r

	def ValidRow( self, r ):
		return bool( r['Date'] )
	
	def GetRows( self ):
		fields = filter( None, self.ws.Range( 'A1:Z1' ).Value[0] )
		rows = itertools.count( 2 )
		rows = itertools.imap( self.GetRow, rows )
		rows = itertools.imap( lambda r: dict( zip( fields, r ) ), rows )
		rows = itertools.takewhile( self.ValidRow, rows )
		rows = itertools.imap( self.FixDate, rows )
		self.rows = rows

default = r'\\merciless\home\jaraco\my documents\projects\financial\transactions.xls' 
if __name__ == '__main__':
	i = MoneyImporter( default )
	i.GetRows()