import threading
import requests
import timeit
import logging

from datetime import datetime, date

from main.apps.core.services.http_request import ApiBase
from main.apps.oems.backend.date_utils import now, sec_diff, add_time
from django.conf import settings
from main.apps.oems.models.cny import CnyExecution
from main.apps.currency.models.fxpair import FxPair

# =============================================================================

def get_exec_config(market_name=None, company_id=None, ticket=None):
    market_name = market_name or ticket.market_name
    company_id = company_id or ticket.company_id
    fxpair = FxPair.get_pair(market_name)
    try:
        ret = CnyExecution.objects.get(company_id=company_id, fxpair_id=fxpair.id)
        if ret: return vars(ret)
    except:
        return None

# =============================================================================

class PangeaSwaggerApi(ApiBase):

    def __init__(self, api_base=None, token=None):

        self.api_base    = api_base
        self.token       = token
        self.fxpairs     = None
        self.fxlookup    = None
        self.currencies  = None
        self.last_prices = None
        self.lock        = threading.Lock()
        self.cache       = {}
        self.mkt_state   = {}
        self.mkt_state_price_refresh = 30.0

    @staticmethod
    def parse_date( date_str ):
        try:
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
        except:
            return date_str

    @staticmethod
    def format_date( dt ):
        if isinstance(dt, str):
            return dt
        else:
            return dt.isoformat()

    def get( self, endpoint, auth=True, return_data=False, paginated=True, loop=True, params=None, **kwargs ):

        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
        }

        if auth:
            headers['Authorization'] = f'Token {self.token}'

        if return_data:
            resp = super().get(endpoint, headers=headers, params=params, verify=False, **kwargs)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                return None
            elif resp.status_code == 500:
                return resp.json()
            resp.raise_for_status()

        done = False
        ret  = []
        while not done:
            print('query', endpoint, params)
            reply = super().get(endpoint, headers=headers, params=params, verify=False, **kwargs)
            if not reply.status_code == 200:
                print(f"ERROR: {endpoint} - {reply.status_code} {reply.content}")
                done = True
                break
            print(f"INFO: {endpoint} Success")
            data  = reply.json()
            if paginated:
                if 'results' in data:
                    ret += data['results']
                if loop and 'next' in data and data['next']:
                    endpoint = data['next']
                    params   = None
                else:
                    done = True
            else:
                ret  = data
                done = True
        return ret

    def post( self, endpoint, auth=True, data=None, **kwargs ):

        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
        }

        if auth:
            headers['Authorization'] = f'Token {self.token}'

        reply = super().post(endpoint, headers=headers, json=data)
        if not reply.status_code == 200:
            # print(f"ERROR: {endpoint} - {reply.status_code} {reply.content}")
            try:
                print('ERROR', reply.status_code )
                print('ERROR MSG', reply.json())
            except:
                pass
            return

        return reply.json()

    # ================================================

    def get_fx_pairs( self, regen=False ):
        if self.fxpairs is None or regen:
            self.fxpairs = {}
            fxpairs = self.get( f'{self.api_base}/currency/fxpairs/', auth=True, paginated=True )
            for row in fxpairs:
                key  = row['id']
                base = row['base_currency']
                cntr = row['quote_currency']
                self.fxpairs[key] = base['mnemonic'] + cntr['mnemonic']
            # self.fxpairs = { row['id']: self.currencies[ row['base_currency'] ]['mnemonic'] + self.currencies[ row['quote_currency'] ]['mnemonic'] for row in fxpairs }
            self.fxlookup = { v: k for k, v in self.fxpairs.items() }
        return self.fxpairs

    def get_currencies( self, regen=False ):
        if self.currencies is None or regen:
            currencies = self.get( f'{self.api_base}/currency/currencies/', auth=True, paginated=False )
            self.currencies = { row['id']: row for row in currencies }
        return self.currencies

    def get_last_price( self, mkt, src='CORPAY', use_cache=True, ):

        cache_key = (mkt, src)

        if use_cache and cache_key in self.mkt_state and sec_diff( now(), self.mkt_state[cache_key]['time'] ) < self.mkt_state_price_refresh:
            return self.mkt_state[cache_key]['last_price']

        if src == 'CORPAY':
            params      = { 'ordering': '-date', 'limit': 1, 'offset': 0, 'base_currency': mkt[:3], 'quote_currency': mkt[3:] }
            last_prices = self.get( f'{self.api_base}/marketdata/spot/corpay', auth=True, loop=False, params=params )
        elif src == 'IBKR':
            currencies = self.get_currencies()
            fx_pairs   = self.get_fx_pairs()
            params      = { 'ordering': 'desc', 'limit': 1, 'offset': 0, 'pair_ids': self.fxlookup[mkt] }
            last_prices = self.get( f'{self.api_base}/marketdata/spot/intra/', auth=True, loop=False, params=params )

        if last_prices:
            
            ret = last_prices[-1]

            if use_cache:
                if mkt in self.mkt_state:
                    self.mkt_state[mkt]['last_price'] = ret
                    self.mkt_state[mkt]['time'] = now()
                else:
                    self.mkt_state[mkt] = { 'last_price': ret, 'time': now() }

            return ret

    # ==================

    def broken_api( self, *args, **kwargs ):
        ret = self.get( f'{self.api_base}/marketdata/spot/blah/', auth=True, loop=False )
        return ret

    def get_trading_sessions( self, mkt, sdt=None ):

        currencies = self.get_currencies()
        fx_pairs   = self.get_fx_pairs()

        if sdt is None: sdt = add_time( datetime.today(), days=-1 )
        if isinstance(sdt, datetime): sdt = sdt.strftime('%Y-%m-%d')

        params = { 'start_date': sdt, 'pair_ids': self.fxlookup[mkt] }
        ret    = self.get( f'{self.api_base}/marketdata/trading_calendar/', auth=True, loop=False, params=params )

        for row in ret:
            row['start_date'] = self.parse_date( row['start_date'] )
            row['end_date']   = self.parse_date( row['end_date'] )

        try:
            ret.sort(key=lambda x: (bool(x['start_date']),x['start_date']))
        except:
            pass

        return ret

    # ====================
    # company broker master

    def get_exec_config(self, market_name=None, company=None, ticket=None, cache_ttl=300, use_cache=True, regen_cache=False):
        market_name = market_name or ticket.market_name
        company_id = company or ticket.get_company().id
        cache_key = (company_id, market_name)
        if use_cache:
            if not regen_cache \
                    and cache_key in self.cache \
                    and now() < self.cache[cache_key]['expire']:
                return self.cache[cache_key]['data']
        data = get_exec_config(market_name=market_name, company_id=company_id)
        # data = self.get( f"{self.api_base}/oems/cny-execution/?company={company}&market={market_name}", return_data=True )
        if data and use_cache:
            self.cache[cache_key] = {'expire': add_time(now(), seconds=cache_ttl), 'data': data}
        return data

    # ====================
    # corpay

    def corpay_spot_rfq( self, from_ccy, to_ccy, amount, lock_side, endpoint='/broker/corpay/spot/rate' ):

        assert amount > 0.0

        data = {
            "payment_currency": from_ccy,
            "settlement_currency": to_ccy,
            "amount": amount,
            "lock_side": lock_side,
        }

        start_time = timeit.default_timer()
        ret = self.post( f'{self.api_base}{endpoint}', data=data )
        logging.info(f"{self.api_base}{endpoint} took {timeit.default_timer() - start_time}")
        return ret

    def corpay_fwd_rfq( self, from_ccy, to_ccy, amount, lock_side, value_date, forward_type="C", endpoint='/broker/corpay/forward/quote' ):

        assert amount > 0.0

        data = {
            "forward_type": forward_type,
            "sell_currency": from_ccy,
            "buy_currency": to_ccy,
            "amount": amount,
            "lock_side": lock_side,
            "maturity_date": self.format_date( value_date ),
            # "open_date_from": self.format_date( date.today() ), # TODO: is this correct? this is for forward/forwards
        }

        return self.post( f'{self.api_base}{endpoint}', data=data )

    # =====================================

    def corpay_mass_payments_spot_rfq( self, from_ccy, to_ccy, amount, lock_side, value_date, settlement_info,
                                        payment_id=None, remitter_id=None, endpoint='/broker/corpay/mass-payments/quote-payments'):

        assert amount > 0.0

        data = {
            "payments": []
        }

        # TODO: could support multi-payments
        
        info = {
            "beneficiary_id": settlement_info['beneficiary_id'],
            "payment_method": settlement_info["payment_method"],
            "amount": amount,
            "lock_side": lock_side,
            "payment_currency": from_ccy,
            "settlement_currency": to_ccy,
            "settlement_method": settlement_info['settlement_method'],
            "settlement_account_id": settlement_info['settlement_account_id'],
            "payment_reference": settlement_info['payment_reference'],
            "purpose_of_payment": settlement_info['purpose_of_payment'],
            "remitter_id": remitter_id,
            "delivery_date": value_date,
            "payment_id": payment_id,
        }

        data['payments'].append(info)

        return self.post( f'{self.api_base}{endpoint}', data=data )

    def corpay_mass_payments_rfq_execute( self, quote_id, session_id, combine_settlements=True, endpoint='/broker/corpay/mass-payments/book-payments' ):

        data = {
            "quote_id": quote_id,
            "session_id": session_id,
            "combine_settlements": combine_settlements
        }

        return self.post( endpoint, data=data )

    def corpay_execute_spot_rfq( self, quote_id, endpoint='/broker/corpay/spot/book-deal' ):

        data = {
            "quote_id": quote_id,
        }

        start_time = timeit.default_timer()
        ret = self.post( f'{self.api_base}{endpoint}', data=data )
        logging.info(f"{self.api_base}{endpoint} took {timeit.default_timer() - start_time}")
        return ret
        
    def corpay_execute_fwd_rfq( self, quote_id, endpoint='/broker/corpay/forward/book-quote' ):

        data = {
            "quote_id": quote_id,
        }

        return self.post( f'{self.api_base}{endpoint}', data=data )

    # ================================

    def get_contracts_by_base( self, base_future, endpoint='/broker/ib/contract' ):
        url = f'{self.api_base}{endpoint}/{base_future}'
        return self.get( url, return_data=True )

    def get_active_contracts_by_base( self, base_future, endpoint='/broker/ib/contract/active' ):
        url = f'{self.api_base}{endpoint}/{base_future}'
        return self.get( url, return_data=True )

    def get_contract_ref( self, symbol, endpoint='/broker/ib/contract/detail' ):
        url = f'{self.api_base}{endpoint}/{symbol}'
        return self.get( url, return_data=True )

# =============================================================================

class PangeaSwaggerMultiApi:
    def __init__( self ):
        self.clients = {}
    def __call__( self, base_url, auth_token ):
        key = (base_url, auth_token)
        if key in self.clients:
            return self.clients[key]
        else:
            client = PangeaSwaggerApi(
                api_base=base_url,
                token=auth_token
            )
            self.clients[key] = client
            return client

# =============================================================================

pangea_client_cache = PangeaSwaggerMultiApi()
pangea_client = pangea_client_cache(settings.DASHBOARD_API_URL, settings.DASHBOARD_API_TOKEN)

# =============================================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--mkt', default='USDJPY')
    parser.add_argument('--action', choices=['price','cal','broken','rfq','rfq_execute'], default='price')
    parser.add_argument('--base-url', default="settings.DASHBOARD_API_URL")
    parser.add_argument('--auth-token', default="settings.DASHBOARD_API_TOKEN")

    args = parser.parse_args()

    if args.action == 'price':
        ret = pangea_client.get_last_price( args.mkt )
    elif args.action == 'cal':
        ret = pangea_client.get_trading_sessions( args.mkt )
    elif args.action == 'broken':
        ret = pangea_client.broken_api()
    elif args.action == 'rfq':
        ret = pangea_client.corpay_spot_rfq( args.mkt[:3], args.mkt[-3:], 1000., 'payment' )
    elif args.action == 'rfq_execute':
        ret  = pangea_client.corpay_spot_rfq( args.mkt[:3], args.mkt[-3:], 1000., 'payment' )      
        ret2 = pangea_client.corpay_execute_spot_rfq( ret['quote_id'] )

