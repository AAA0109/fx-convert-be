from decimal import Decimal
from typing import Union, List

from django.db.models import QuerySet
from hdlib.DateTime.Date import Date

from main.apps.account.models.company import Company
from main.apps.core import utils
from main.apps.core.models import Config
from main.apps.core.utils.slack import SlackNotification
from main.apps.risk_metric.services.market_risk_service import MarketRiskService


def get_movement_warnings(data, config):
    """
    Injest the format of output from:
        main.apps.risk_metric.services.market_risk_service.MarketRiskService.get_market_changes_for_fxpair

    :param data: get_market_changes_for_fxpair return
    :param config: Config naming path
    :return: {
        '[pair]':{
            '[period]':{
                '[indicator]':{
                    '[element]':True,
                    ...
                }
            }
        }
    }
    """
    config = Config.get_config(config).value

    result = dict()
    for currency, cur_data in data.items():
        for period, pdata in config.items():
            for l1, l1data in pdata.items():
                for l2, threshold in l1data.items():
                    abs_value = abs(cur_data[period][l1][l2])
                    if abs_value > threshold:
                        if not result.get(currency):
                            result[currency] = {}
                        if not result[currency].get(period):
                            result[currency][period] = {}
                        if not result[currency][period].get(l1):
                            result[currency][period][l1] = {}
                        result[currency][period][l1].update({l2: True})

    return result


class CurrencyMovementNotification(object):
    def __init__(self, companies: Union[QuerySet, List[Company]]):
        self.companies = companies

    @staticmethod
    def _company_blocks(company: Company):
        data = MarketRiskService.get_market_changes_for_company(Date.now(), company)
        warnings = get_movement_warnings(data, 'volatility/movement/threshold')
        if not warnings:
            return None

        yield {
            "type": "divider"
        }

        url = utils.get_frontend_url(path='dashboard/cashflows')
        yield {
            "type": "context",
            "elements": [
                {
                    "text": f":pushpin: *{company.name}*  |  <{url}|View CF>",
                    "type": "mrkdwn"
                }
            ]
        }

        yield {
            "type": "divider"
        }

        # build currency/period movement list
        fields = []
        for currency, cdata in warnings.items():
            text = ''
            for period, pdata in cdata.items():
                text += f"\n`{period}`"
                for l1, l1data in pdata.items():
                    for l2 in l1data.keys():
                        val = Decimal("{0:.2f}".format(round(data[currency][period][l1][l2], 2)))
                        text += f"\n{l1}/{l2}: {val}"
            fields.append({
                "type": "mrkdwn",
                "text": f"*{currency}*{text}"
            })

        # returning pairs build pairs
        for i in range(len(fields) // 2):
            yield {
                "type": "section",
                "fields": [fields.pop(0), fields.pop(0)]
            }

        # return the remain
        if fields:
            yield {
                "type": "section",
                "fields": fields
            }

    def send(self):
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":alert: | Large currency movements | :alert:"
                }
            }
        ]

        for company in self.companies:
            gen = self._company_blocks(company)
            for item in gen:
                blocks.append(item)

        SlackNotification().send_blocks(blocks=blocks)
