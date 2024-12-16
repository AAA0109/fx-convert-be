import base64

from django.db import models
from drf_simple_invite.models import InvitationToken

from main.apps.account.models import User


class ExtendInvitationToken(models.Model):
    invitation_token = models.OneToOneField(InvitationToken, on_delete=models.CASCADE, null=False,
                                            related_name="extend")
    inviter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, default=None)

    @staticmethod
    def get_encoded_token(invitation_token: InvitationToken):
        encoded = base64.urlsafe_b64encode(str(invitation_token.id).encode()).decode()
        return encoded
