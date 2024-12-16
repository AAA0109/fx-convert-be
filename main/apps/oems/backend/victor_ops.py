import os
import uuid
import json

# import tempfile
import requests

from django.conf import settings

# ======================================

API_ENDPOINT = "https://api.victorops.com/api-public/v1"

"""
# GET v1/user/{user}/oncall/schedule
# GET v1/team/{team}/oncall/schedule
# PATCH /api-public/v1/team/{team}/oncall/user
"""

# =======================================


def override_shift(from_user, to_user, team):
    team = team.lower()
    url = "%s/team/%s/oncall/user" % (API_ENDPOINT, team)
    body = {"fromUser": from_user, "toUser": to_user}
    headers = {
        "X-VO-Api-Id": settings.VICTOR_OPS_API_ID,
        "X-VO-Api-Key": settings.VICTOR_OPS_API_KEY,
        "content-type": "application/json",
        "accept": "application/json",
    }
    req = requests.patch(url, data=json.dumps(body), headers=headers)
    return req

def get_alert_info( entity_id ):
    url = f"{API_ENDPOINT}/alerts/{entity_id}"
    headers = {
        "X-VO-Api-Id": settings.VICTOR_OPS_API_ID,
        "X-VO-Api-Key": settings.VICTOR_OPS_API_KEY,
        "content-type": "application/json",
        "accept": "application/json",
    }
    req = requests.get(url, headers=headers)
    return req

def ack_incident( username: str, alert_id: str, action='resolve' ): # action=ack
    url = f"{API_ENDPOINT}/incidents/{action}"
    body = {"userName": username, "incidentNames": [alert_id]}
    headers = {
        "X-VO-Api-Id": settings.VICTOR_OPS_API_ID,
        "X-VO-Api-Key": settings.VICTOR_OPS_API_KEY,
        "content-type": "application/json",
        "accept": "application/json",
    }
    req = requests.patch(url, data=json.dumps(body), headers=headers)
    return req

# ======================================

# TODO: send alert email integration

# ===========================

"""
    # https://help.victorops.com/knowledge-base/victorops-restendpoint-integration/
    Message Types: CRITICAL, WARNING, INFO, ACKNOWLEDGMENT, RECOVERY
"""

class VICTOR_OPS_MESSAGE_TYPES:
    CRITICAL = 'CRITICAL'
    WARNING = 'WARNING'
    INFO = 'INFO'
    ACKNOWLEDGMENT = 'ACKNOWLEDGMENT'
    RECOVERY = 'RECOVERY'

def victor_ops_msg(
    msg,
    entity_id=None,
    message_type=VICTOR_OPS_MESSAGE_TYPES.CRITICAL,
    entity_display_name="from Pangea Trading Alert System. ",
    ack_msg="ok",
):

    if entity_display_name and entity_display_name[-1] != " ":
        entity_display_name += " "

    ret = {
        "entity_id": entity_id,
        "message_type": message_type,
        "entity_display_name": entity_display_name + msg,  # HACK TO READ MSG.
        "ack_msg": ack_msg,
        "state_message": msg,
    }

    return ret


# =======================================

def send_alert(body, route):

    headers = {
        # "X-VO-Api-Id": settings.VICTOR_OPS_API_ID,
        # "X-VO-Api-Key": settings.VICTOR_OPS_API_KEY,
        "content-type": "application/json",
        "accept": "application/json",
    }

    data = json.dumps(body)
    url  = f"https://alert.victorops.com/integrations/generic/20131114/alert/3d45f005-c1a1-4ee3-ad98-bc1a0d61f372/{route}"
    req  = requests.post(url, data=data, headers=headers)

    return req

# =======================================

def call_victor_ops(
    msg=None,
    routing_key=None,
    entity_id=None,
    message_type=VICTOR_OPS_MESSAGE_TYPES.CRITICAL,
    entity_display_name="from Pangea Trading Alert System. ",
    **kwargs
):

    if routing_key is None or not settings.VICTOR_OPS_ENABLED:
        return

    if not entity_id:
        entity_id = str(uuid.uuid4())

    body = victor_ops_msg(
        msg,
        entity_id,
        message_type=message_type,
        entity_display_name=entity_display_name,
        **kwargs
    )

    req = send_alert(body, routing_key)

    if req.status_code != 200:
        print(req.status_code, req.reason, req.text)

    return req

# =======================================

if __name__ == "__main__":

    if True:
        req = call_victor_ops( "This is a test call to our exec desk which will automatically call whomever is on-duty based on our New York, Asia, London schedule.",
                        "EXEC_DESK",
                        entity_display_name="from Pangea Exec Desk. ",
        )
        info = get_alert_info( req.json()['entity_id'] )
