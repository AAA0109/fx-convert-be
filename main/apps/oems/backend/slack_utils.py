from datetime import date, datetime, timedelta

from main.apps.core.utils.slack import SlackNotification, slack_dispatch

# =============

def slack_format( x ):
	if x is None:
		return "NULL"
	if isinstance(x, (int,float)):
		return f'{x:,.0f}'
	elif isinstance(x, (date, datetime)):
		return x.isoformat()
	return x

def make_markdown_kv(kvpairs, include_nulls=False):
	return "\n".join([f"`{k}`: `{slack_format(v)}`" for k, v in kvpairs.items() if include_nulls or v is not None])

# =============

def make_markdown_ladder( kvpairs, include_nulls=False ):
	return ({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": make_markdown_kv(kvpairs, include_nulls=include_nulls),
			}
		})

def make_input_section( slug, placeholder, ):
	return ({
		"type": "input",
		"block_id": f"{slug}_input",
		"element": {
			"type": "plain_text_input",
			"action_id": slug,
			"placeholder": {
				"type": "plain_text",
				"text": placeholder,
			}
		},
		"label": {
			"type": "plain_text",
			"text": slug.replace('_',' ').title(),
		}
	})

def make_buttons( buttons ):

	ret = {
		"type": "actions",
		"elements": []
	}

	for key, button in buttons.items():

		if isinstance(button, dict):
			typ = button.get('type','plain_text')
			title = button['text'].replace('_',' ').title()
			value = button['value']
		else:
			typ = 'plain_text'
			title = button.replace('_',' ').title()
			value = key

		ret['elements'].append(
			{
				"type": "button",
				"text": {
					"type": typ,
					"text": title
				},
				"value": value,
				"action_id": key,
			}
		)

	return ret

def make_header( text:str ) -> dict:
	return {
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": text,
				"emoji": True
			}
		}

# ============================

if __name__ == "__main__":

	import sys

	kv_pairs = {
		'STATUS': 'PENDING',
	#	'EXPIRY': datetime.now() + timedelta(minutes=10),
		'FROM_CCY': 'USD',
		'TO_CCY': 'INR',
		'LOCK_SIDE': 'PAYMENT',
		'AMOUNT': 100000.0,
	}

	quote_form = []

	quote_form.append( make_markdown_ladder(kv_pairs) )
	quote_form.append( make_input_section( 'rate', 'Enter the rate' ) )
	#quote_form.append( make_input_section( 'quote_id', 'Enter the quote_id' ) )
	quote_form.append( make_buttons(['submit','cancel']) )

	# sn.delete_message(channel="C04E0NJET63", thread_ts=t)

	if '--send' in sys.argv:
		sn = SlackNotification()

		resp = sn.send_blocks(channel="testing-notifications-public", text='Put all the order information up here in a nice format.', blocks=quote_form, return_data=True)

		print( resp )

		kv_pairs2 = {
			'STATUS': 'DONE',
			'FROM_CCY': 'USD',
			'TO_CCY': 'INR',
			'LOCK_SIDE': 'PAYMENT',
			'AMOUNT': 100000.0,
			'RATE': 83.3,
		}

		new_quote_form = []
		new_quote_form.append( make_markdown_ladder(kv_pairs2) )

		if input('Edit Message? ').lower() == 'y':
			resp2 = sn.edit_message(channel=resp['channel'], thread_ts=resp['ts'], text=resp['message']['text'], blocks=new_quote_form)

		if input('Delete Message? ').lower() == 'y':
			sn.delete_message(channel=resp2['channel'], thread_ts=resp2['ts'])
