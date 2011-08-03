from ZODB import DB
import ZEO.ClientStorage

import logging
logging.basicConfig( level = logging.DEBUG )

db = DB( ZEO.ClientStorage.ClientStorage( ( 'localhost', 8100 ) ) )

