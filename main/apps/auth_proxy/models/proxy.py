from django.contrib.auth.models import Group as BaseGroup
from drf_simple_invite.models import InvitationToken as BaseInvitationToken
from django_rest_passwordreset.models import ResetPasswordToken as BaseResetPasswordToken
from trench.models import MFAMethod as BaseMFAMethod

from main.apps.account.models.user import User as BaseUser
from main.apps.history.models.account_management import UserActivity as BaseUserActivity


class User(BaseUser):

    class Meta:
        proxy = True


class UserActivity(BaseUserActivity):

    class Meta:
        proxy = True


class Group(BaseGroup):

    class Meta:
        proxy = True


class MFAMethod(BaseMFAMethod):

    class Meta:
        proxy = True


class InvitationToken(BaseInvitationToken):

    class Meta:
        proxy = True


class ResetPasswordToken(BaseResetPasswordToken):

    class Meta:
        proxy = True
