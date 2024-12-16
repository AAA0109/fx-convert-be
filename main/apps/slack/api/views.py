import json
import traceback
import logging

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from django.conf import settings

from main.apps.core.utils.slack import SlackNotification, slack_dispatch
import main.apps.slack.api.registry

# ==================

logger = logging.getLogger(__name__)

class SlackEventsView(APIView):

    slack_notify = SlackNotification(verify=True)
    permission_classes = [AllowAny] # TODO: test and switch to SlackPerms

    def post(self, request, **kwargs):

        if not self.slack_notify.signature_verifier.is_valid_request(self.request.body, request.headers):
            logger.debug('slack verifier rejected message: {self.request.body} {request.headers}')
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            if 'payload' in request.data:
                data = json.loads(request.data['payload'])
            else:
                data = request.data
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            if data['type'] == 'url_verification':
                response_dict = {'challenge': data['challenge']}
                return Response(status=status.HTTP_200_OK, data=response_dict)
        except:
            pass

        # dict_keys(['type', 'user', 'api_app_id', 'token', 'container', 'trigger_id', 'team', 'enterprise', 'is_enterprise_install', 'channel', 'message', 'state', 'response_url', 'actions'])

        # x['container']['message_ts'] x['container']['channel_id'] # to get the thing
        # x['actions'], x['channel] tells you teh channel
        # x['whatever']
        try:
            content = slack_dispatch.dispatch( data )
        except:
            print(traceback.format_exc())
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if content:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)

