from typing import Sequence, Optional, Type
import logging
import pytz

import pandas as pd
from django.db import models

from hdlib.DateTime.Date import Date

from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.base import IbkrApiHandler
from main.apps.ibkr.models.future_contract import FutureContract, FutureContractIntra
from main.apps.marketdata.models import  DataCut

logger = logging.getLogger(__name__)


class IbkrFutureContractIntraApiHandler(IbkrApiHandler):
   model: FutureContractIntra

   __tz = pytz.timezone('US/Eastern')

   def __init__(self, data_cut_type: DataCut.CutType, model: Type[models.Model]):
        super().__init__(data_cut_type, model)

   def get_data_from_api(self) -> Optional[pd.DataFrame]:
      now = Date.now()
      date = now.astimezone(tz=self.__tz)
      rows = []
      contracts = []

      future_contract_list = FutureContract.objects.all()
      for future_contract in future_contract_list:
         if (future_contract.base != None or future_contract.local_symbol != None) and future_contract.con_id != None :
            contract = self.api.get_contract(type="future", symbol=future_contract.fut_symbol,
               lastTradeDateOrContractMonth=future_contract.lcode_long, localSymbol=future_contract.local_symbol, conId=future_contract.con_id)
            contracts.append(contract)

      contracts = self.client.qualifyContracts(*contracts)
      for contract in contracts:
         self.client.reqMktData(contract, 'BidAsk', True, False)
      rows = []
      for contract in contracts:
         ticker = self.client.ticker(contract)
         self.client.sleep(0.75)
         if not ticker.hasBidAsk():
               # TODO: log no data
               # TODO: Fire event
               continue
         rows.append([contract.id, contract.base, date, ticker.marketPrice(), ticker.bid, ticker.ask])
      for contract in contracts:
         self.client.cancelMktData(contract)

      self.df = pd.DataFrame(
         rows,
         columns=["future_contract_id", "base", "date", "rate", "rate_bid", "rate_ask"]
      )
      return self.df

   def create_models_with_df(self) -> Sequence[FutureContractIntra]:
      return [
         self.model(
            future_contract_id=row["future_contract_id"],
            base=row["base"],
            date=row["date"],
            rate=row["rate"],
            rate_bid=row["rate_bid"],
            rate_ask=row["rate_ask"],
         )
         for _, row in self.df.iterrows()
      ]

   def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return ['future_contract_id']
