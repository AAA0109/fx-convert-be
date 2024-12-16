from django.db import models
from django.utils.translation import gettext_lazy as _
from main.apps.account.models.company import Company

from main.apps.account.models.user import User


class ApprovalMethod(models.TextChoices):
        NO_APPROVAL = 'no_approval', _('No Approval Required')
        APPROVAL_REQUIRED = 'approval_required', _('Approval Required')


class ApprovalTriggerMethod(models.TextChoices):
        ALL_APPROVALS = 'all_approvals', _('All Transactions Require Approval')
        MIN_APPROVAL = 'min_approval', _('Approval Required If Exceeding Min Trigger')


class ApprovalLevel(models.TextChoices):
        APPROVAL_LEVEL_1 = 'approval_level_1', _('Approval Level 1')
        APPROVAL_LEVEL_2 = 'approval_level_2', _('Approval Level 2')


class ApprovalType(models.TextChoices):
        SINGLE_APPROVAL = 'single_approval', _('Single Approval')
        DOUBLE_APPROVAL = 'double_approval', _('Dual Approval')


class CompanyApprovalSetting(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, null=False,
                                   related_name='approval_setting')

    approval_method = models.CharField(max_length=50, choices=ApprovalMethod.choices,
                                       default=ApprovalMethod.NO_APPROVAL)

    approval_trigger = models.CharField(max_length=50, choices=ApprovalTriggerMethod.choices,
                                        default=ApprovalTriggerMethod.ALL_APPROVALS, null=True)

    min_approval_trigger_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True)

    enable_dual_approval = models.BooleanField(default=False,
                                               help_text="Enable dual concurrent approval?",
                                               verbose_name="Enable Dual Approval")

    def save(self, *args, **kwargs):
        if self.approval_method == ApprovalMethod.NO_APPROVAL:
            self.approval_trigger = None
            self.min_approval_trigger_amount = None
            self.enable_dual_approval = False
        super(CompanyApprovalSetting, self).save(*args, **kwargs)


class ApprovalLevelLimit(models.Model):
    class Meta:
        unique_together = (('company', 'approval_level'),)

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)

    approval_level = models.CharField(max_length=50, choices=ApprovalLevel.choices, default=ApprovalLevel.APPROVAL_LEVEL_1)

    max_approval_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True)


class GroupApprovalAuthorization(models.Model):
    class Meta:
        unique_together = (('company', 'group', 'approval_level'),)

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)

    group = models.CharField(max_length=50, choices=User.UserGroups.choices)

    approval_level = models.CharField(choices=ApprovalLevel.choices, null=True)


class CompanyApprovalBypass(models.Model):

    class Meta:
        verbose_name = 'Company Approval Bypass User'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
