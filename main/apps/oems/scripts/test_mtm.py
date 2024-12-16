from unittest import skip

from main.apps.oems.backend.mtm import MarkToMarket
@skip("Test script exclude from unit test")
def run():

	server = MarkToMarket()
	server.mark_to_market()

