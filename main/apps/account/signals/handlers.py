import logging

from django.db.models import Model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created
from drf_simple_invite.models import InvitationToken
from drf_simple_invite.signals import invitation_token_created

from main.apps.account.models import User, ExtendInvitationToken
from main.apps.account.signals import activation_token_created
from main.apps.broker.services.configuration import BrokerConfigurationService
from main.apps.notification.utils.email import (
    send_reset_password_token_email, send_invitation_token_email, send_user_activation_email
)

logger = logging.getLogger("root")


@receiver(pre_save, sender=User, dispatch_uid="initialize_phone_confirmed_for_new_users")
def initialize_phone_confirmed_for_new_users(sender, instance, raw, using, update_fields, *args, **kwargs):
    if instance.id is None and instance.phone_confirmed is None:
        instance.phone_confirmed = False


@receiver(post_save, sender=User, dispatch_uid="generate_user_activation_token_handler")
def generate_user_activation_token_handler(sender, instance: User, created: bool, *args, **kwargs):
    if not created:
        return
    if not instance.is_invited:
        # if the user is not invited we generate an activation token
        # invited user will activate through password confirm flow
        User.generate_activation_token(instance)


@receiver(activation_token_created)
def activation_token_created_handler(sender, instance, activation_token, *args, **kwargs):
    send_user_activation_email(user=instance, activation_token=activation_token)


@receiver(reset_password_token_created)
def reset_password_token_created_handler(sender, instance, reset_password_token, *args, **kwargs):
    send_reset_password_token_email(reset_password_token=reset_password_token)


@receiver(invitation_token_created)
def invitation_token_created_handler(sender: Model, instance: User, invitation_token: str, user: User, *args,
                                     **kwargs):
    if 'inviter' in kwargs:
        inviter = kwargs.get('inviter')
        send_invitation_token_email(inviter=inviter, invitee=user, invitation_token=invitation_token)


@receiver(post_save, sender=InvitationToken, dispatch_uid="create_extend_invitation_token_handler")
def create_extend_invitation_token(sender, instance: InvitationToken, created: bool, *args, **kwargs):
    if not created:
        return
    extend_invitation_token = ExtendInvitationToken(
        invitation_token=instance
    )
    extend_invitation_token.save()
