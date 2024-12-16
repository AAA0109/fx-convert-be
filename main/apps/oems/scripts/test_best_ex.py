import uuid

from main.apps.oems.backend.trading_utils import get_reference_data
from main.apps.oems.backend.exec_utils import get_best_execution_status

def run(*args):

    status = get_best_execution_status( 'USDJPY', check_spot=True )
    print( status )


