import logging
from datetime import date
from rest_framework import serializers
from typing import List, Optional, Union
from main.apps.account.models.company import Company
from main.apps.account.models.user import User
from main.apps.approval.models.approval import (
    ApprovalLevelLimit,
    CompanyApprovalBypass,
    CompanyApprovalSetting,
    ApprovalMethod,
    ApprovalTriggerMethod,
    ApprovalLevel,
    GroupApprovalAuthorization
)
from main.apps.approval.services.limit import CompanyLimitService
from main.apps.currency.models.currency import Currency


logger = logging.getLogger(__name__)


class CompanyApprovalService:
    company:Company

    def __init__(self, company:Company) -> None:
        self.company = company

    def get_company_approval_setting(self) -> Optional[CompanyApprovalSetting]:
        """
        Get Company approval setting
        """
        try:
            approval_setting = CompanyApprovalSetting.objects.get(company=self.company)
        except CompanyApprovalSetting.DoesNotExist:
            approval_setting = None
        return approval_setting

    def get_company_approval_level(self) -> List[ApprovalLevelLimit]:
        """
        Get Company approval level
        """
        approval_levels = ApprovalLevelLimit.objects.filter(company=self.company)
        return list(approval_levels)

    def get_company_group_approval(self, approval_level:str) -> List[str]:
        """
        Get Company approval group by approval level
        """
        groups = GroupApprovalAuthorization.objects\
            .filter(company=self.company, approval_level=approval_level).values_list('group', flat=True)
        return groups

    def populate_approvers_by_level(self, approval_groups:List[str]) -> List[User]:
        users = User.objects.filter(company=self.company)
        approvers = set()
        for group in approval_groups:
            for user in users:
                if user.groups.filter(name=group).exists():
                    approvers.add(user)
        return list(approvers)

    def is_transaction_require_approval(self, converted_amount:float) -> bool:
        """
        Check if transaction amount require an approval
        """
        approval_setting = self.get_company_approval_setting()

        if approval_setting is None or \
            approval_setting.approval_method == ApprovalMethod.NO_APPROVAL:
            return False

        if approval_setting.approval_trigger == ApprovalTriggerMethod.MIN_APPROVAL and \
            approval_setting.min_approval_trigger_amount is not None and \
            converted_amount <= approval_setting.min_approval_trigger_amount:
            return False

        return True

    def populate_approver(self, converted_amount:float) -> List[User]:
        approval_levels = self.get_company_approval_level()

        approval_level_1 = None
        approval_level_2 = None

        for approval_level in approval_levels:
            if approval_level_1 is not None and approval_level_2 is not None:
                break
            elif approval_level.approval_level == ApprovalLevel.APPROVAL_LEVEL_1:
                approval_level_1 = approval_level
                continue
            elif approval_level.approval_level == ApprovalLevel.APPROVAL_LEVEL_2:
                approval_level_2 = approval_level
                continue

        approvers = []
        if approval_level_1 is not None and converted_amount <= approval_level_1.max_approval_amount:
            approval_groups = self.get_company_group_approval(approval_level=approval_level_1.approval_level)
            approvers = self.populate_approvers_by_level(approval_groups=approval_groups)
        elif approval_level_2 is not None and converted_amount <= approval_level_2.max_approval_amount:
            approval_groups = self.get_company_group_approval(approval_level=approval_level_2.approval_level)
            approvers = self.populate_approvers_by_level(approval_groups=approval_groups)

        bypass_users = CompanyApprovalBypass.objects.filter(user__company=self.company)
        for bypass_user in bypass_users:
            if not bypass_user.user in approvers:
                approvers.append(bypass_user.user)

        return approvers


class ApproverProvider:
    company:Company

    def __init__(self, company:Company) -> None:
        self.company = company

    def get_transaction_approvers(self,currency:Union[Currency, str], amount:float,
                                   value_date=Union[str, date]) -> List[User]:
        limit_service = CompanyLimitService(company=self.company)
        discounted_amount, is_exceeding_limit = limit_service.validate_transaction_limit(currency=currency,
                                                                                   amount=amount,
                                                                                   value_date=value_date)

        if is_exceeding_limit:
            raise serializers.ValidationError(detail={
                'success': False,
                'message': 'Amount exceeding company limit'
            })

        if not is_exceeding_limit:
            approval_svc = CompanyApprovalService(company=self.company)
            require_approval = approval_svc.is_transaction_require_approval(converted_amount=discounted_amount)
            if require_approval:
                approvers = approval_svc.populate_approver(converted_amount=discounted_amount)
                return approvers

        return []
