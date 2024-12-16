import json
import traceback

from drf_spectacular.types import OpenApiTypes

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from django.conf import settings

from main.apps.broker.services.registry import BrokerCallbacks
from main.apps.broker.services.webhooks import * # register everything

# =======

class BrokerEventsView(APIView):

	permission_classes = [AllowAny] # TODO: test and switch to SlackPerms

	def post(self, request, **kwargs):

		broker = kwargs.get('broker')
		action = kwargs.get('action')

		# print('dispatch callback for', broker, action)
		# TODO: check for validity as well or put in dispatch?
		return BrokerCallbacks.dispatch( broker, action, request.data )

		if content:
			return Response(status=status.HTTP_200_OK)
		else:
			return Response(status=status.HTTP_204_NO_CONTENT)

# =======
