from django.dispatch import Signal

__all__ = [
    'ibkr_deposit_pending',
    'ibkr_deposit_processed',
    'ibkr_deposit_rejected',
    'ibkr_withdraw_pending',
    'ibkr_withdraw_processed',
    'ibkr_withdraw_rejected'
]

"""
Signal arguments: sender, instance
"""
ibkr_deposit_pending = Signal()

"""
Signal arguments: sender, instance
"""
ibkr_deposit_processed = Signal()

"""
Signal arguments: sender, instance
"""
ibkr_deposit_rejected = Signal()

"""
Signal arguments: sender, instance
"""
ibkr_withdraw_pending = Signal()

"""
Signal arguments: sender, instance
"""
ibkr_withdraw_processed = Signal()

"""
Signal arguments: sender, instance
"""
ibkr_withdraw_rejected = Signal()
