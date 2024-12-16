
from rest_framework.response import Response
from rest_framework import status

from main.apps.broker.services.registry import BrokerCallbacks

# TODO

def handle_nium_callback( payload ):
	print('handle nium callback here', payload)
	return Response(status=status.HTTP_200_OK)

def handle_nium_webhook( payload ):
	print('handle nium webhook here', payload)
	return Response(status=status.HTTP_200_OK)

BrokerCallbacks.register( 'nium', 'callback', handle_nium_callback )
BrokerCallbacks.register( 'nium', 'webhook', handle_nium_webhook )
