from unittest import skip

from django.conf import settings

from main.apps.dataprovider.services.collectors.runner import CollectorRunner

from main.apps.dataprovider.services.collectors.adapters.corpay_rfq_collector import CorpayRfqCollector
from main.apps.dataprovider.services.collectors.adapters.verto_rfq_collector import VertoRfqCollector
from main.apps.dataprovider.services.collectors.adapters.openex_collector import OpenExCollector


from main.apps.dataprovider.services.collectors.cache import RedisCache
from main.apps.dataprovider.services.collectors.publisher import GcpPubSub


# =========
@skip("Test script exclude from unit test")
def run():

	mkts = ['USDJPY']
	bases = ['USD']


	kwargs = { 'writer': None, 'publisher': GcpPubSub, 'cache': RedisCache }

	collector1 = CorpayRfqCollector( f'{settings.APP_ENVIRONMENT}1', mkts, ['SPOT','SN','1W','1M','3M'], **kwargs )
	collector2 = VertoRfqCollector( f'{settings.APP_ENVIRONMENT}1', mkts, **kwargs )
	collector3 = OpenExCollector( f'{settings.APP_ENVIRONMENT}1', bases, **kwargs )

	# runner = CollectorRunner(collector3)
	runner = CollectorRunner(collector1,collector2,collector3)
	runner.run_forever()
