import uuid

# ==================

def get_netting_key( request ):
	return (request['buy_currency'], request['sell_currency'], request['lock_side'],request['value_date'],request.get('transaction_group'))

def get_batch_info( request ):
	return { fld: request.get(fld) for fld in ('amount','cashflow_id','transaction_id','customer_id','beneficiary_id','settle_account_id','beneficiaries','settlement_info') }

# ==================

def process_net_requests( net_requests ):

	# if 1 request, no netting necessary
	# if multiple, track the info and send one net order for disbursement
	ret = []

	for key, value in net_requests.values():

		net_req, batch_tracking = value

		if len(batch_tracking) == 1:
			ret.append(net_req)
			continue

		for fld in ('cashflow_id','transaction_id','customer_id','beneficiary_id','settle_account_id','beneficiaries','settlement_info'):
			net_req[fld] = None

		net_req['beneficiaries'] = []
		net_req['settlement_info'] = []

		for row in batch_tracking:
			for bene in row['beneficiaries']:
				if 'amount' not in bene:
					bene['amount'] = row['amount']
				if 'amount_pct' not in bene:
					bene['amount_pct'] = (row['amount']/net_req['amount'])
				net_req['beneficiaries'].append(bene)

		# put net information somewhere (most likely beneficiaries)
		net_req.mass_payment_info = batch_tracking

		ret.append(net_req)

	return ret

def batch_and_net( requests, do_netting=False ):

	# TODO: net transactions by currency, side, and transaction_group??
	# if no transaction_group provided net those together?
	# while netting, keep track of settle_account_id and beneficiary_id

	# figure out what you do with transactions that net off
	# do we generate fake fills? we still have to move money
	# so we need to test that

	if not do_netting:
		return requests

	# TODO: pull out bene_id and settle_account_id and add to beneficiaries/settlement_info
	# do we validate the orders now?

	net_requests = {}

	# TODO: maximum requests
	# Do we want to net by settlement_account_id or allow multi-payins?
	
	for req in requests:

		key = get_netting_key( req )

		if key in net_requests:
			net_req, batch_tracking = net_requests[key]
			info = get_batch_info( req )
			if len(batch_tracking) >= 500: # corpay max mass payouts
				old_batch = net_requests.pop(key)
				new_key = f'{key}-{uuid.uuid4()}'
				net_requests[new_key] = old_batch
				net_requests[key] = (req, [info])
			else:
				batch_tracking.append(info)
				net_req['amount'] += req['amount']
		else:
			info = get_batch_info( req )
			batch_tracking = [info]
			net_requests[key] = (req, batch_tracking)

	ret = process_net_requests( net_requests )

	return ret

