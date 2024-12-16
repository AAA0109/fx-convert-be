from django.dispatch import Signal

__all__ = [
    'activation_token_created'
]

"""
Signal arguments: instance, activation_token
"""
activation_token_created = Signal()
