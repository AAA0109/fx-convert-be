import logging
from typing import List, Optional, Tuple, Union
from main.apps.account.models.company import Company
from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.models.cny import CnyExecution


logger = logging.getLogger(__name__)


class CompanyCnyExecutionProvider:
    company:Company
    fx_pair:FxPair
    cny_execution:CnyExecution = None

    def __init__(self, company:Company, fx_pair:Optional[Union[FxPair, str]] = None) -> None:
        self.company = company
        self.fx_pair = fx_pair

        if isinstance(fx_pair, str):
            self.fx_pair = FxPair.get_pair(pair=fx_pair)

        if fx_pair is not None:
            try:
                self.cny_execution = CnyExecution.objects.get(company=self.company,
                                                            fxpair=self.fx_pair)
            except Exception as e:
                logger.error(str(e), exc_info=True)
                self.cny_execution = None

            if self.cny_execution is None:
                logger.info("Cny by original pair not found, Find by inverse pair...")
                try:
                    self.cny_execution = CnyExecution.objects.get(company=self.company,
                                                                fxpair=FxPair.get_inverse_pair(pair=self.fx_pair))
                except Exception as e:
                    logger.error(str(e), exc_info=True)
                    self.cny_execution = None

    def get_fwd_rfq_type(self, cny_exec:Optional[CnyExecution] = None) -> Optional[str]:
        if cny_exec is not None:
            return cny_exec.fwd_rfq_type

        if not self.cny_execution:
            return None
        return self.cny_execution.fwd_rfq_type

    def is_ndf(self, cny_exec:Optional[CnyExecution] = None) -> Tuple[Optional[bool], Optional[str]]:
        """
        Check if market is ndf
        False => fwd_rfq_type == api
        True => fwd_rfq_type != api

        return (is_ndf:bool, fwd_rfq_type:str)
        """

        fwd_rfq_type = self.get_fwd_rfq_type(cny_exec=cny_exec)

        if fwd_rfq_type is None:
            return None, fwd_rfq_type

        if fwd_rfq_type == CnyExecution.RfqTypes.API:
            return False, fwd_rfq_type
        return True, fwd_rfq_type

    def populate_company_ndf_pairs(self, cny_execs:Optional[List[CnyExecution]] = None) -> List[dict]:
        if cny_exec is None:
            cny_execs = CnyExecution.objects.filter(company=self.company, active=True).distinct('fxpair')

        ndf_currencies = []
        for cny_exec in cny_execs:
            is_ndf, fwd_rfq_type = self.is_ndf(cny_exec=cny_exec)

            if is_ndf:
                ndf_currencies.append({
                    'pairs': cny_exec.fxpair.name,
                    'is_ndf': is_ndf,
                    'fwd_rfq_type': fwd_rfq_type
                })

        return ndf_currencies
