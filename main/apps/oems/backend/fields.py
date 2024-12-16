

# ==============================

CONFIRMATION_FIELDS = {
    'market_name': 'Currency Pair',
    'side': 'Side',
    'buy_currency': 'Buy Currency',
    'sell_currency': 'Sell Currency',
    'lock_side': 'Lock Side',
    'trader': 'Trader',
    'value_date': 'Value Date',
    'all_in_done': 'All In Amount',
    'all_in_cntr_done': 'All In Counter Amount',
    'all_in_rate': 'All In Rate',
    'transaction_id': 'Transaction ID',
}

CONFIRMATION_NDF_FIELDS = {
    'market_name': 'Currency Pair',
    'side': 'Side',
    'buy_currency': 'Buy Currency',
    'sell_currency': 'Sell Currency',
    'lock_side': 'Lock Side',
    'trader': 'Trader',
    'value_date': 'Value Date',
    'fixing_date': 'Fixing Date',
    'all_in_done': 'All In Amount',
    'all_in_cntr_done': 'All In Counter Amount',
    'all_in_rate': 'All In Rate',
    'spot_rate': 'Spot Rate',
    'fwd_points': 'Forward Points',
    'transaction_id': 'Transaction ID',
}

# ==============================

EXECUTE_RETURN_FIELDS = {
    'ticket_id': None,
    'external_state': 'status',
    'action': None,
    'spot_rate': None,
    'fwd_points': None,
    'all_in_rate': None,
    'value_date': None,
    'transaction_time': None,
    'payment_amount': None,
    'delivery_fee': None,
    'total_cost': None,
}

# ==============================

RFQ_RETURN_FIELDS = {
    'ticket_id': None,
    'external_state': 'status',
    'action': None,
    'external_quote': 'quote',
    'external_quote_expiry': 'quote_expiry',
    'quote_indicative': 'indicative',
    'spot_rate': None,
    'fwd_points': None,
    'quote_fee': None,
    'fee': None,
    'value_date': None,
    'transaction_time': None,
    'transaction_amount': None,
    'delivery_fee': None,
    'total_cost': None,
}

# ==============================

EXEC_RFQ_RETURN_FIELDS = {
    'ticket_id': None,
    'external_state': 'status',
    'action': None,
    'external_quote': 'quote',
    'external_quote_expiry': 'quote_expiry',
    'spot_rate': None,
    'fwd_points': None,
    'quote_fee': None,
    'fee': None,
    'value_date': None,
}

