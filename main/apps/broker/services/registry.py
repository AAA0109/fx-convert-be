from rest_framework.response import Response
from rest_framework import status

# ================

class BrokerCallbacks:

	callbacks = {}

	@classmethod
	def register( cls, broker, action, function_like ):

		key = (broker,action)

		# print( 'register', key )
		if key in cls.callbacks:
			raise ImportError(f'{key} used in multiple dispatching for broker webhooks.')

		cls.callbacks[key] = function_like

	@classmethod
	def dispatch( cls, broker, action, payload ):

		key = (broker,action)

		# print('check dispatch', key, key in cls.callbacks)

		if key in cls.callbacks:
			return cls.callbacks[key]( payload )
		else:
			# TODO: could return 500
			return Response(status=status.HTTP_200_OK)

# ================
