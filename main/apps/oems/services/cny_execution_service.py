import csv
from main.apps.account.models.company import Company
from main.apps.currency.models import FxPair
from main.apps.oems.models.cny import CnyExecution
from main.apps.oems.backend.trading_utils import get_reference_data
from main.apps.oems.backend.utils import load_yml, Expand

MAJORS = {'USD','EUR','GBP','CAD','MXN','AUD'}

def initialize_company(company: Company):

    spot_broker = 'CORPAY'
    fwd_broker = 'CORPAY'

    path = Expand(__file__) + '/../migrations/ccy_minimums.csv'
    ccy_map = {}

    with open( path ) as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            row['min'] = float(row['min'])
            row['max'] = float(row['max'])
            ccy_map[ row['ccy'] ] = row

    for fxpair in FxPair.get_pairs():

        mkt = fxpair.market
        if 'RUB' in mkt: continue

        ref = get_reference_data(mkt)
        if not ref: continue

        from_ccy, to_ccy = mkt[:3], mkt[3:]

        if from_ccy not in MAJORS and to_ccy not in MAJORS:
            continue

        if to_ccy in ccy_map:
            min_order_size_to = ccy_map[to_ccy]['min']
            max_order_size_to = ccy_map[to_ccy]['max']
        else:
            min_order_size_to = 1.0
            max_order_size_to = 5000000.0

        if from_ccy in ccy_map:
            min_order_size_from = ccy_map[from_ccy]['min']
            max_order_size_from = ccy_map[from_ccy]['max']
        else:
            min_order_size_from = 1.0
            max_order_size_from = 5000000.0

        spot_rfq_type = CnyExecution.RfqTypes.API
        fwd_rfq_type = CnyExecution.RfqTypes.API if ref['CCY_TYPE'] == 'Spot' else CnyExecution.RfqTypes.MANUAL

        CnyExecution.objects.create(
            company=company,
            fxpair=fxpair,
            default_broker=spot_broker,
            spot_broker=spot_broker,
            fwd_broker=fwd_broker,
            spot_rfq_type = spot_rfq_type,
            fwd_rfq_type = fwd_rfq_type,
            min_order_size_to = min_order_size_to,
            max_order_size_to = max_order_size_to,
            min_order_size_from = min_order_size_from,
            max_order_size_from = max_order_size_from,
        )
