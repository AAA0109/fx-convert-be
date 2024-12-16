from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin
from trench.admin import MFAMethodAdmin
from django_rest_passwordreset.admin import ResetPasswordTokenAdmin

from main.apps.account.admin import UserAdmin
from main.apps.history.admin import UserActivityAdmin

from main.apps.auth_proxy.models.proxy import (
    Group,
    InvitationToken,
    MFAMethod,
    ResetPasswordToken,
    User,
    UserActivity
)


# Register your models here.
admin.site.register(User, UserAdmin)
admin.site.register(UserActivity, UserActivityAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(MFAMethod, MFAMethodAdmin)
admin.site.register(InvitationToken)
admin.site.register(ResetPasswordToken, ResetPasswordTokenAdmin)
