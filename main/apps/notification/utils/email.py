from datetime import datetime, time
from typing import List, Tuple

from django_rest_passwordreset.models import ResetPasswordToken
from drf_simple_invite.models import InvitationToken
import pytz

from main.apps.account.models import User, ExtendInvitationToken, CompanyJoinRequest, Company, CashFlow
from main.apps.broker.models import BrokerAccount
from main.apps.corpay.models import ManualForwardRequest
from main.apps.currency.models.fxpair import FxPair
from main.apps.ibkr.models import DepositResult, WireInstruction
from main.apps.margin.models import MarginDetail
from main.apps.marketdata.services.cutoff_service import CutoffProvider
from main.apps.oems.backend.ccy_utils import determine_rate_side
from main.apps.oems.backend.exec_utils import get_best_execution_status
from main.apps.payment.models import Payment
from main.apps.margin.services.margin_service import ProjectedMargin
from main.apps.notification.services.email.templates import CompanyNonSellableForwardEmailTemplate, PaymentApprovalRequestEmailTemplate, PaymentApprovedRequestEmailTemplate
from main.apps.notification.services.email.templates import ResetPasswordEmailTemplate, \
    InvitationEmailTemplate, UserActivationEmailTemplate, CompanyJoinRequestEmailTemplate, MarginReceivedEmailTemplate, \
    LowMarginEmailTemplate, DepositRequiredEmailTemplate, PositionsLiquidatingEmailTemplate, \
    PendingApprovalEmailTemplate
from main.apps.notification.services.email_service import send_email_template
from main.apps.settlement.models.beneficiary import Beneficiary


def send_reset_password_token_email(reset_password_token: ResetPasswordToken):
    template = ResetPasswordEmailTemplate(
        reset_password_token=reset_password_token
    )
    send_email_template(template=template, recipient_list=[reset_password_token.user.email])


def send_invitation_token_email(inviter: User, invitee: User, invitation_token: str):
    template = InvitationEmailTemplate(
        invitation_token=invitation_token,
        inviter=inviter,
        invitee=invitee
    )
    send_email_template(template=template, recipient_list=[invitee.email])


def send_user_activation_email(user: User, activation_token: str):
    template = UserActivationEmailTemplate(
        activation_token=activation_token
    )
    send_email_template(template=template, recipient_list=[user.email])


def send_company_join_request_email(account_owner: User, company_join_request: CompanyJoinRequest):
    template = CompanyJoinRequestEmailTemplate(
        account_owner=account_owner,
        company_join_request=company_join_request
    )
    send_email_template(template=template, recipient_list=[account_owner.email])


def send_margin_received_email(company: Company, deposit_result: DepositResult):
    template = MarginReceivedEmailTemplate(
        company=company,
        deposit_result=deposit_result
    )
    send_email_template(template=template, recipient_list=[company.account_owner.email])


def send_low_margin_email(broker_account: BrokerAccount,
                          margin: MarginDetail,
                          forcast_margin: ProjectedMargin,
                          wire_instruction: WireInstruction):
    template = LowMarginEmailTemplate(
        broker_account=broker_account,
        wire_instruction=wire_instruction,
        margin=margin,
        forecast_margin=forcast_margin
    )
    send_email_template(template=template, recipient_list=[broker_account.company.account_owner.email])


def send_deposit_required_email(broker_account: BrokerAccount,
                                margin: MarginDetail,
                                forcast_margin: ProjectedMargin,
                                wire_instruction: WireInstruction):
    template = DepositRequiredEmailTemplate(
        broker_account=broker_account,
        wire_instruction=wire_instruction,
        margin=margin,
        forecast_margin=forcast_margin
    )
    send_email_template(template=template, recipient_list=[broker_account.company.account_owner.email])


def send_positions_liquidating_email(broker_account: BrokerAccount,
                                     wire_instruction: WireInstruction,
                                     margin: MarginDetail):
    template = PositionsLiquidatingEmailTemplate(
        broker_account=broker_account,
        wire_instruction=wire_instruction,
        margin=margin,
        forecast_margin=None
    )
    send_email_template(template=template, recipient_list=[broker_account.company.account_owner.email])


def send_pending_approval_email(cashflow: CashFlow):
    template = PendingApprovalEmailTemplate(cashflow=cashflow)
    company = cashflow.account.company
    users = User.objects.filter(
        company=company,
        groups__in=[User.UserGroups.CUSTOMER_ADMIN, User.UserGroups.CUSTOMER_MANAGER]
    )
    send_email_template(template=template, recipient_list=[user.email for user in users])


def resend_email_template(template, email) -> bool:
    user = User.get_user_by_email(email)
    if template == 'reset_password':
        reset_password_token = ResetPasswordToken.objects.filter(user=user).order_by('-created_at').first()
        send_reset_password_token_email(reset_password_token)
        return True
    if template == 'user_activation':
        send_user_activation_email(user, user.activation_token)
        return True
    if template == 'invitation_token':
        invitation_token = InvitationToken.objects.filter(user=user).order_by('-created_at').first()
        inviter = invitation_token.extend.inviter
        invitee = invitation_token.user
        invitation_token = ExtendInvitationToken.get_encoded_token(invitation_token=invitation_token)
        send_invitation_token_email(inviter=inviter, invitee=invitee, invitation_token=invitation_token)
        return True

    return False


def send_non_sellable_forward_email(company: Company, manual_forward_requests: List[ManualForwardRequest]):
    template = CompanyNonSellableForwardEmailTemplate(
        company=company,
        manual_forward_requests=manual_forward_requests,
    )
    send_email_template(template=template, recipient_list=template.recipient_list)


def get_approval_email_context_data_and_recipients(payment:Payment,
                                                   is_request:bool=True) -> Tuple[dict, List[User]]:
    recipients = []
    approvers = payment.get_approvers()
    for approver in approvers:
        recipients.append(approver.email)

    pair = payment.get_payment_pair()

    value_date = payment.get_value_date()
    execution_strategy = payment.get_execution_strategy()
    buy_amount = payment.get_amount(to_currency_format=True)
    tz = pytz.timezone('America/New_York')
    tdy = datetime.now(tz).date()
    cutoff_time = tz.localize(datetime.combine(tdy, time(16)))\
        .astimezone(pytz.timezone('UTC'))

    fxpair, side = determine_rate_side(pair.base_currency, pair.quote_currency)
    market = fxpair.market
    status = get_best_execution_status(market)
    cutoff_provider = CutoffProvider(market=market, session=status['session'])
    cutoff_time = cutoff_provider.modify_cutoff(cutoff_time=cutoff_time)
    cutoff_time = cutoff_time.astimezone(tz=tz)

    beneficiary = Beneficiary().get_beneficiary_display(beneficiary_id=payment.destination_account_id)
    cutoff_date = datetime.strftime(cutoff_time, '%x')
    cutoff_hmp = datetime.strftime(cutoff_time, '%I:%M %p')

    context_data = {
        'cutoff_date': f"{cutoff_date} @ {cutoff_hmp} EST",
        'execution_strategy': execution_strategy,
        'currency': pair.market if pair is not None else 'N/A',
        'buy_amount': buy_amount,
        'value_date': datetime.strftime(value_date, '%Y-%m-%d'),
        'beneficiary': beneficiary,
        'url_path': 'payments/view',
        'query_params': {'id': payment.pk},
        'approvers': ', '.join([approver.get_full_name() for approver in approvers]),
        "creator": payment.create_user.get_full_name(),
    }
    if not is_request:
        recipients = [payment.create_user.email]
    return context_data, recipients


def send_approval_request_email(payment: Payment):
    """
    Send payment approval request email
    """
    context_data, recipients = get_approval_email_context_data_and_recipients(payment=payment)
    template = PaymentApprovalRequestEmailTemplate(context_data=context_data)
    send_email_template(template=template, recipient_list=recipients)


def send_approved_request_email(payment: Payment):
    """
    Send approved payment approval request email
    """
    context_data, recipients = get_approval_email_context_data_and_recipients(payment=payment,
                                                                              is_request=False)
    template = PaymentApprovedRequestEmailTemplate(context_data=context_data)
    send_email_template(template=template, recipient_list=recipients)
