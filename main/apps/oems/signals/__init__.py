from django.dispatch import Signal

__all__ = [
    'oems_ticket_external_state_change',
    'oems_ticket_internal_state_change',
]

"""
Signal arguments: sender, instance, state
"""
oems_ticket_external_state_change = Signal()


"""
Signal arguments: sender, instance, state
"""
oems_ticket_internal_state_change = Signal()
