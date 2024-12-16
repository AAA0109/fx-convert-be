import json
import uuid
from datetime import datetime

import requests

from main.apps.core.utils.slack import slack_dispatch
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.services.initial_marketdata import get_recent_data
from main.apps.oems.backend.slack_utils import make_markdown_ladder, make_buttons, make_input_section
from main.apps.oems.backend.utils import jsonify
from main.apps.oems.models.life_cycle import LifeCycleEvent
from main.apps.oems.models.manual_request import ManualRequest
from main.apps.oems.models.ticket import Ticket
from main.apps.settlement.models.wallet import Wallet


# =======


def extract_input_values(payload):
    values = payload['state']['values']
    button_values = {}
    for k, v in values.items():
        for fld, vv in v.items():
            button_values[fld] = vv['value']  # vv['type'] for type information
    return button_values


def try_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def handle_rfq_submit(payload):
    user = payload['user']

    channel_id = payload['container']['channel_id']
    thread_ts = payload['container']['message_ts']
    button_values = extract_input_values(payload)

    if not button_values['rate']:
        raise ValueError

    mreq_id = int(payload['message']['text'])
    mreq = ManualRequest.objects.get(pk=mreq_id)

    if mreq.slack_channel != channel_id and mreq.slack_ts != thread_ts:
        pass  # should not be possible

    if button_values['rate']:
        mreq.booked_rate = float(button_values['rate'])
        mreq.exec_notes = button_values['note']
        mreq.exec_user = user['name']
        mreq.close()
    else:
        raise ValueError


def handle_execute_submit(payload):
    values = payload['state']['values']
    user = payload['user']

    channel_id = payload['container']['channel_id']
    thread_ts = payload['container']['message_ts']
    button_values = extract_input_values(payload)

    if not not button_values['all_in_rate']:
        raise ValueError

    if not button_values['amount'] and not button_values['cntr_amount']:
        raise ValueError

    mreq_id = int(payload['message']['text'])
    mreq = ManualRequest.objects.get(pk=mreq_id)

    if mreq.slack_channel != channel_id and mreq.slack_ts != thread_ts:
        pass  # should not be possible

    if button_values['rate'] and button_values['amount']:
        mreq.booked_all_in_rate = try_float(button_values['all_in_rate'])
        mreq.booked_amount = try_float(button_values['amount'])
        mreq.booked_cntr_amount = try_float(button_values['cntr_amount'])
        mreq.broker_id = button_values['broker_id']
        mreq.exec_notes = button_values['note']
        mreq.exec_user = user['name']
        mreq.close()
    else:
        raise ValueError


def handle_execute_cancel(payload):
    user = payload['user']

    channel_id = payload['container']['channel_id']
    thread_ts = payload['container']['message_ts']

    mreq_id = int(payload['message']['text'])
    mreq = ManualRequest.objects.get(pk=mreq_id)

    if mreq.slack_channel != channel_id and mreq.slack_ts != thread_ts:
        pass  # should not be possible

    # should there be a REJECT as well?

    if not mreq.is_cancelled():
        button_values = extract_input_values(payload)
        try:
            if button_values['note']:
                mreq.exec_notes = button_values['note']
        except:
            pass
        mreq.status = mreq.Status.CANCELED
        mreq.exec_user = user['name']
        mreq.save()
        mreq.close()


# =======

def handle_life_cycle_request(payload):
    text = payload['text']
    tokens = list(map(str.strip, text.split(' ')))

    if not tokens or not tokens[0]:
        resp = 'USAGE: <ticket-id>'
        rtype = 'ephemeral'
    else:
        ticket_id = uuid.UUID(tokens[0].strip())
        ticket = Ticket.objects.get(ticket_id=ticket_id)
        events = LifeCycleEvent.objects.filter(ticket_id=ticket_id)
        resp = []
        if ticket: resp.append('\n'.join(f'{k}: {v}' for k, v in ticket.export().items() if v is not None))
        if events: resp.append('\n'.join([event.text for event in events]))
        if resp:
            resp = '\n'.join(resp)
            rtype = 'in_channel'
        else:
            resp = 'no ticket found with ticket_id: {ticket_id}'
            rtype = 'ephemeral'

    data = {
        # "response_type": "in_channel",  # Or "ephemeral" for a private response
        "response_type": rtype,
        "text": resp,
    }
    response = requests.post(payload['response_url'], json=data)
    return True


def handle_rate_request(payload):
    text = payload['text']
    tokens = list(map(str.strip, text.split(' ')))

    if not tokens:
        resp = 'USAGE: <MARKET> <[optional] SPOT (default) or TENOR or fwd date>'
    else:
        mkt = tokens[0].upper()
        tenor = tokens[1].upper() if len(tokens) > 1 else 'SPOT'
        if len(mkt) != 6:
            resp = 'ERROR: bad market'
        elif tenor == 'TODAY' or tenor == 'SPOT':
            fxpair = FxPair.get_pair(mkt)
            value_date = Ticket.Tenors.SPOT  # if tenor == Ticket.Tenors.SPOT else
            spot_rate, fwd_points, ws_feed = get_recent_data(fxpair, value_date)
            try:
                bid = spot_rate['bid'] + fwd_points['bid']
                ask = spot_rate['ask'] + fwd_points['ask']
                mid = spot_rate['mid'] + fwd_points['mid']
                time = datetime.utcnow().strftime("%H:%M:%S")
                resp = f"{time} BID: {bid:.5f} ASK: {ask:.5f} MID: {mid:.5f}"
            except:
                resp = 'ERROR'
        elif False:  # tenor in tenors, calc value date, forward provde the points and the rate + spot ref
            ...
        elif False:  # is_date(tenor), check date and provide price
            ...
        else:
            resp = 'ERROR'

    data = {
        # "response_type": "in_channel",  # Or "ephemeral" for a private response
        "response_type": "ephemeral",
        "text": resp,
    }
    response = requests.post(payload['response_url'], json=data)
    return True


def handle_rfq_request(payload):
    text = payload['text']
    tokens = list(map(str.strip, text.split(' ')))

    data = {
        # "response_type": "in_channel",  # Or "ephemeral" for a private response
        "response_type": "ephemeral",
        "text": 'Not implemented yet',
    }

    response = requests.post(payload['response_url'], json=data)
    return True


# ============================

BOOK_TICKET = 'ephemeral'


def failed_bt(payload):
    data = {
        # "response_type": "in_channel",  # Or "ephemeral" for a private response
        "response_type": BOOK_TICKET,
        "text": "Failed... try again",
        "delete_original": True,
    }
    response = requests.post(payload['response_url'], json=data)
    return True


def handle_bt_accept(payload):
    try:
        values = json.loads(payload['actions'][0]['value'])
    except:
        return failed_bt(payload)

    print(values)

    data = {
        # "response_type": "in_channel",  # Or "ephemeral" for a private response
        "response_type": BOOK_TICKET,
        "text": "Accepted!",
        "delete_original": True,
    }

    response = requests.post(payload['response_url'], json=data)

    return True


def handle_bt_submit(payload):
    response_url = payload['response_url']

    button_values = extract_input_values(payload)

    for v in button_values.values():
        if v is None: return failed_bt(payload)

    # map company
    data = {}

    # map company
    # check value date

    data['company'] = button_values['company']
    data['buy_ccy'] = button_values['buy_ccy']
    data['sell_ccy'] = button_values['sell_ccy']
    data['buy_amount'] = float(button_values['buy_amount'])
    data['sell_amount'] = float(button_values['sell_amount'])
    data['all_in_rate'] = float(button_values['all_in_rate'])
    data['value_date'] = button_values['value_date']

    data = jsonify(data)

    quote_form = []

    ladder = make_markdown_ladder(button_values, include_nulls=True)
    quote_form.append(ladder)
    quote_form.append(
        make_buttons({'book_ticket_accept': {'text': 'accept', 'value': data}, 'book_ticket_reject': 'reject'}))

    data = {
        # "response_type": "in_channel",  # Or "ephemeral" for a private response
        "response_type": BOOK_TICKET,
        "text": "Confirm",
        "replace_original": True,
        "delete_original": True,
        "blocks": quote_form,
    }

    response = requests.post(payload['response_url'], json=data)

    return True


def handle_bt_cancel(payload):
    data = {
        # "response_type": "in_channel",  # Or "ephemeral" for a private response
        "response_type": BOOK_TICKET,
        "delete_original": True,
    }

    response = requests.post(payload['response_url'], json=data)

    return True


def handle_book_ticket(payload):
    text = payload['text']
    channel_id = payload['channel_id']
    user_id = payload['user_id']
    username = payload['user_name']

    required_fields = ['company', 'buy_ccy', 'buy_amount', 'sell_ccy', 'sell_amount', 'all_in_rate', 'value_date']

    quote_form = []
    for fld in required_fields:
        quote_form.append(make_input_section(fld, f'Enter the {fld}'))
    quote_form.append(make_buttons({'book_ticket_submit': 'submit', 'book_ticket_cancel': 'cancel'}))

    data = {
        # "response_type": "in_channel",  # Or "ephemeral" for a private response
        "response_type": BOOK_TICKET,
        "text": 'Book Manual Ticket',
        "blocks": quote_form,
    }

    response = requests.post(payload['response_url'], json=data)

    return True

# =======

def handle_wallet_rem_req(payload):
    form_data = extract_input_values(payload)
    wallet_id = form_data.get('wallet_id', None)
    if wallet_id is not None and wallet_id != "":
        try:
            wallet = Wallet.objects.get(wallet_id=wallet_id)
            wallet.status = Wallet.WalletStatus.INACTIVE
            wallet.save()

            from main.apps.core.utils.slack import SlackNotification

            channel_id = payload['container']['channel_id']
            thread_ts = payload['container']['message_ts']

            slack_client = SlackNotification()
            slack_client.delete_message(channel=channel_id, thread_ts=thread_ts)
        except:
            pass

# =======

slack_dispatch.register_action('rfq_submit_action', handle_rfq_submit)
slack_dispatch.register_action('rfq_cancel_action', handle_execute_cancel)
slack_dispatch.register_action('execute_submit_action', handle_execute_submit)
slack_dispatch.register_action('execute_cancel_action', handle_execute_cancel)

# commands

slack_dispatch.register_command('/rate', handle_rate_request)
slack_dispatch.register_command('/rfq', handle_rfq_request)
slack_dispatch.register_command('/execute', handle_rfq_request)
slack_dispatch.register_command('/summary', handle_life_cycle_request)

# manual booking
slack_dispatch.register_command('/book-ticket', handle_book_ticket)
slack_dispatch.register_action('book_ticket_submit', handle_bt_submit)
slack_dispatch.register_action('book_ticket_accept', handle_bt_accept)
slack_dispatch.register_action('book_ticket_cancel', handle_bt_cancel)
slack_dispatch.register_action('book_ticket_reject', handle_bt_cancel)

# wallet actions
slack_dispatch.register_action('wallet_rem_req', handle_wallet_rem_req)
