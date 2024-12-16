import io
from abc import ABC, abstractmethod
from typing import Optional, Iterable, List, Dict

import pandas as pd
try:
    import weasyprint
except Exception as e:
    print("Warning: could not import weasyprint")
from django.conf import settings
from django.core.files.base import ContentFile
from django.template import Context, Template
from django.template.loader import get_template
from django.utils import formats
from django_rest_passwordreset.models import ResetPasswordToken
from post_office.models import EmailTemplate

from main.apps.account.models import User, CompanyJoinRequest, Company, CashFlow
from main.apps.account.services.cashflow.email import CashflowEmailService
from main.apps.billing.services.email import InvoiceEmailService
from main.apps.broker.models import BrokerAccount
from main.apps.core import utils
from main.apps.core.models import Config
from main.apps.corpay.models import ManualForwardRequest
from main.apps.corpay.models.fx_balance import FXBalance
from main.apps.hedge.models import FxForwardPosition
from main.apps.ibkr.models import DepositResult, WireInstruction
from main.apps.margin.models import MarginDetail
from main.apps.margin.services.margin_service import ProjectedMargin


EMAIL_TEMPLATES = [
    'reset_password',
    'user_activation',
    'invitation_token'
]


class AttachmentTemplate(ABC):
    def build(self, context_data) -> Dict[str, ContentFile]:
        raise NotImplementedError


class PDFAttachmentTemplate(AttachmentTemplate):
    def __init__(self, template_name, attachment_name='', language=''):
        self.tpl = EmailTemplate.objects.get(name=template_name, language=language)
        self.attachment_name = attachment_name or self.tpl.subject

    def build(self, context_data) -> Dict[str, ContentFile]:
        context = Context(context_data)
        attachment_name = Template(self.attachment_name).render(context)
        html_content = Template(self.tpl.html_content).render(context)
        html_content = html_content.replace(settings.STATIC_URL, str(settings.STATIC_ROOT) + '/')
        document = weasyprint.HTML(string=html_content, base_url=settings.BACKEND_DIR).render()

        buffer = io.BytesIO()
        document.write_pdf(buffer)
        buffer.seek(0)

        return {
            attachment_name: ContentFile(buffer.read())
        }


class BaseEmailTemplate(ABC):
    template = ''
    context_data = {}
    subject = ''

    def __init__(self, *args, **kwargs):
        self.init_context_data()

    @staticmethod
    def get_frontend_url(path: str, query_params=None):
        if query_params is None:
            query_params = dict()
        return utils.get_frontend_url(path=path, **query_params)

    @abstractmethod
    def render(self, format: str):
        raise NotImplementedError("render not defined")

    @abstractmethod
    def init_context_data(self):
        raise NotImplementedError("context data not initialized")

    def get_attachments(self):
        """
        Return the attachments for the template format
        :return: {'filename.ext': Content()}
        """
        return {}


class PostOfficeEmailTemplate(BaseEmailTemplate, ABC):
    language = ''
    attachments = []  # type: List[AttachmentTemplate]

    @property
    def tpl(self) -> EmailTemplate:
        if not hasattr(self, '_tpl'):
            setattr(self, '_tpl', EmailTemplate.objects.get(name=self.template, language=self.language))
        return getattr(self, '_tpl')

    @property
    def subject(self):
        _context = Context(self.context_data)
        _content = self.tpl.subject
        return Template(_content).render(_context)

    def render(self, format: str):
        _context = Context(self.context_data)
        _content = self.tpl.html_content if format == 'html' else self.tpl.content
        return Template(_content).render(_context)

    def get_attachments(self) -> Dict[str, ContentFile]:
        """
        Return the attachments for the template format
        :return: {'filename.ext': Content()}
        """
        result = {}
        for attachment in self.attachments:
            result.update(attachment.build(self.context_data))
        return result


class FileEmailTemplate(BaseEmailTemplate, ABC):
    app = ''
    subject = ''

    def render(self, format: str):
        template_path = self._get_email_template_path(format=format)
        file_template = get_template(template_path)
        return file_template.render(self.context_data)

    @classmethod
    def _get_email_template_path(cls, format: str):
        return f"{cls.app}/email/{format}/{cls.template}.{format}"


class ResetPasswordEmailTemplate(FileEmailTemplate):
    app = 'account'
    template = 'reset_password'
    subject = "Rest your password for {title}".format(title="Pangea Prime")

    def __init__(self, reset_password_token: ResetPasswordToken):
        self.reset_password_token = reset_password_token
        super().__init__()

    def init_context_data(self):
        url = self.get_frontend_url(
            path='set_new_password',
            query_params={
                "token": self.reset_password_token.key
            }
        )
        self.context_data['url'] = url


class InvitationEmailTemplate(FileEmailTemplate):
    app = 'account'
    template = 'invitation'
    subject = "You have been invited to join {title}".format(title="Pangea Prime")

    def __init__(self, invitation_token: str, inviter: User, invitee: User):
        self.invitation_token = invitation_token
        self.inviter = inviter
        self.invitee = invitee
        super().__init__()

    def init_context_data(self):
        url = self.get_frontend_url(
            path='activation/create_account',
            query_params={
                "invitation_token": self.invitation_token
            }
        )
        self.context_data = {
            "url": url,
            "inviter_name": self.inviter.get_full_name()
        }


class UserActivationEmailTemplate(FileEmailTemplate):
    app = 'account'
    template = 'user_activation'
    subject = "Verify your email to start using {title}".format(title="Pangea Prime")

    def __init__(self, activation_token: str):
        self.activation_token = activation_token
        super().__init__()

    def init_context_data(self):
        url = self.get_frontend_url(
            path='activation/verify-email',
            query_params={
                "activation_token": self.activation_token
            }
        )
        self.context_data = {
            "url": url
        }


class CompanyJoinRequestEmailTemplate(FileEmailTemplate):
    app = 'account'
    template = 'company_join_request'
    subject = 'A user is requesting to join your company on {title}'.format(title="Pangea Prime")

    def __init__(self, account_owner: User, company_join_request: CompanyJoinRequest):
        self.account_owner = account_owner
        self.company_join_request = company_join_request
        super().__init__()

    def init_context_data(self):
        approve_url = self.get_frontend_url(
            path="company_join_request/approve",
            query_params={
                "company_join_request_id": self.company_join_request.pk
            }
        )
        reject_url = self.get_frontend_url(
            path="company_join_request/reject",
            query_params={
                "company_join_request_id": self.company_join_request.pk
            }
        )
        self.context_data = {
            "requester": self.company_join_request.requester,
            "approve_url": approve_url,
            "reject_url": reject_url
        }


class CompanyNonSellableForwardEmailTemplate(PostOfficeEmailTemplate):
    template = 'company_non_sellable_forward'

    def __init__(self, company: Company, manual_forward_requests: Iterable[ManualForwardRequest]):
        self.company = company
        self.manual_forward_requests = manual_forward_requests
        super().__init__()

    @property
    def recipient_list(self):
        emails = [self.company.rep.email]

        item = Config.objects.get(path='corpay/order/email_recipients')
        for val in item.value.split(','):
            emails.append(val)

        return emails

    def init_context_data(self):
        self.context_data = {
            "company_rep": self.company.rep.get_full_name(),
            "company_name": self.company.name,
            "items": []
        }
        for item in self.manual_forward_requests:
            self.context_data["items"].append({
                "currency_from": item.pair.base_currency,
                "currency_to": item.pair.quote_currency,
                "rate": "[TBD]",
                "amount_to": item.amount,
                "date": item.delivery_date,
            })


class MarginReceivedEmailTemplate(FileEmailTemplate):
    app = 'margin'
    template = 'margin_received'
    subject = 'Margin Received'

    def __init__(self, company: Company, deposit_result: DepositResult):
        self.company = company
        self.deposit_result = deposit_result
        super().__init__()

    def init_context_data(self):
        amount = self.deposit_result.amount
        date_received = self.deposit_result.modified
        method = 'Wire Transfer'

        url = self.get_frontend_url(
            path="dashboard/margin"
        )

        self.context_data = {
            "amount": amount,
            "date_received": date_received,
            "from": False,  # TODO: Need to get the deposited from bank info if possible
            "method": method,
            "url": url
        }


class MarginEmailTemplate(FileEmailTemplate, ABC):
    app = 'margin'

    def __init__(self, broker_account: BrokerAccount, wire_instruction: WireInstruction):
        self.wire_instruction = wire_instruction
        self.company = broker_account.company
        self.broker_account = broker_account
        super().__init__()

    def get_wire_instruction_context_data(self):
        return {
            "bank_name": self.wire_instruction.bank_name,
            "bank_address": self.wire_instruction.bank_address,
            "beneficiary_name": self.wire_instruction.beneficiary_name,
            "beneficiary_address": self.wire_instruction.beneficiary_address,
            "beneficiary_account_number": self.wire_instruction.beneficiary_account_number,
            "swift_bic_code": self.wire_instruction.swift_bic_code,
            "wire_reference": f"{self.broker_account.broker_account_name}/{self.company.name}"
        }


class MarginErrorEmailTemplate(MarginEmailTemplate):
    def __init__(self,
                 broker_account: BrokerAccount,
                 wire_instruction: WireInstruction,
                 margin: MarginDetail,
                 forecast_margin: Optional[ProjectedMargin]):
        self.margin = margin
        self.forecast_margin = forecast_margin
        super().__init__(broker_account, wire_instruction)

    def init_context_data(self):
        margin_total = self.margin.excess_liquidity
        recommended_deposit = self.margin.margin_requirement
        margin_health_score = self.margin.get_margin_health().ratio
        forecast_date = self.forecast_margin.date if self.forecast_margin else None
        forecast_margin_heath = self.forecast_margin.health_score() if self.forecast_margin else None

        url = self.get_frontend_url(
            path="dashboard/margin"
        )

        wire_instruction_data = self.get_wire_instruction_context_data()
        context_data = {
            "margin_total": margin_total,
            "recommended_deposit": recommended_deposit,
            "margin_health_score": margin_health_score,
            "forecast_date": forecast_date,
            "forecast_margin_heath": forecast_margin_heath,
            "url": url
        }
        self.context_data = {**context_data, **wire_instruction_data}


class DepositRequiredEmailTemplate(MarginErrorEmailTemplate):
    template = "deposit_required"
    subject = "Deposit Required"

    def __init__(self,
                 broker_account: BrokerAccount,
                 wire_instruction: WireInstruction,
                 margin: MarginDetail,
                 forecast_margin: Optional[ProjectedMargin]):
        super().__init__(broker_account, wire_instruction, margin, forecast_margin)


class PositionsLiquidatingEmailTemplate(MarginErrorEmailTemplate):
    template = "positions_liquidating"
    subject = "Positions Liquidating"

    def __init__(self,
                 broker_account: BrokerAccount,
                 wire_instruction: WireInstruction,
                 margin: MarginDetail,
                 forecast_margin: Optional[ProjectedMargin]):
        super().__init__(broker_account, wire_instruction, margin, forecast_margin)


class LowMarginEmailTemplate(MarginErrorEmailTemplate):
    template = 'low_margin'
    subject = 'Low Margin'

    def __init__(self,
                 broker_account: BrokerAccount,
                 wire_instruction: WireInstruction,
                 margin: MarginDetail,
                 forecast_margin: Optional[ProjectedMargin]):
        super().__init__(broker_account, wire_instruction, margin, forecast_margin)

    def init_context_data(self):
        margin_total = self.margin.excess_liquidity
        recommended_deposit = self.margin.margin_requirement
        margin_health_score = self.margin.get_margin_health().ratio
        forecast_date = self.forecast_margin.date if self.forecast_margin else None
        forecast_margin_heath = self.forecast_margin.health_score() if self.forecast_margin else None
        deposit_by = forecast_date - 3

        url = self.get_frontend_url(
            path="dashboard/margin"
        )

        wire_instruction_data = self.get_wire_instruction_context_data()
        context_data = {
            "margin_total": margin_total,
            "recommended_deposit": recommended_deposit,
            "deposit_by": deposit_by,
            "margin_health_score": margin_health_score * 100,
            "forecast_date": forecast_date,
            "forecast_margin_heath": forecast_margin_heath * 100,
            "url": url
        }
        self.context_data = {**context_data, **wire_instruction_data}


class PendingApprovalEmailTemplate(FileEmailTemplate):
    app = 'account'
    template = 'pending_approval'
    subject = 'Hedge Pending: Approval Needed'

    def __init__(self, cashflow: CashFlow):
        self.cashflow = cashflow
        self.cashflow_email_service = CashflowEmailService()
        super().__init__()

    def init_context_data(self):
        self.context_data = {
            "name": self.cashflow.name,
            "amount": self.cashflow.amount,
            "currency": f"{self.cashflow.currency.name} ({self.cashflow.currency.mnemonic})",
            "direction": "Receiving" if self.cashflow.amount > 0 else "Paying",
            "payment_type": self.cashflow_email_service.get_payment_type(cashflow=self.cashflow),
            "payment_date": self.cashflow_email_service.get_payment_date(cashflow=self.cashflow),
            "portfolio": self.cashflow.account.name,
            "url": self.get_frontend_url(path="dashboard")
        }


class InvoiceEmailTemplate(FileEmailTemplate):
    app = 'billing'
    template = 'invoice'
    subject = "Upcoming Invoice for {title}".format(title="Pangea Prime")

    def __init__(self, company: Company):
        self.company = company
        self.invoice_email_service = InvoiceEmailService(company)
        super().__init__()

    def init_context_data(self):
        self.context_data = self.invoice_email_service.get_context_data()
        self.context_data['url'] = self.get_frontend_url(path='account/history/fees')
        self.context_data['link_payment_url'] = self.get_frontend_url(path='account/settings/banking')


class ForwardEmailTemplate(PostOfficeEmailTemplate):
    template = 'forward'

    def __init__(self, cashflow: CashFlow):
        self.cashflow = cashflow
        self.cashflow_email_service = CashflowEmailService()
        super().__init__()

    def init_context_data(self):
        self.context_data = {
            "name": self.cashflow.name,
            "amount_usd": abs(self.cashflow_email_service.convert_currency_rate(self.cashflow.currency,
                                                                                self.cashflow.amount)),
            "amount": abs(self.cashflow.amount),
            "currency": self.cashflow.currency,
            "direction": "Receiving" if self.cashflow.amount > 0 else "Paying",
            "payment_type": self.cashflow_email_service.get_payment_type(cashflow=self.cashflow),
            "payment_date": self.cashflow_email_service.get_payment_date(cashflow=self.cashflow),
            "url": self.get_frontend_url(path="manage/overview", query_params={'cashflow_id': self.cashflow.pk})
        }


class ForwardCustomerEditEmailTemplate(PostOfficeEmailTemplate):
    template = 'forward_customer_edit'

    def __init__(self, cashflow: CashFlow):
        self.cashflow = cashflow
        self.cashflow_email_service = CashflowEmailService()
        super().__init__()

    def init_context_data(self):
        self.context_data = {
            "name": self.cashflow.name,
            "link_support_url": self.get_frontend_url(path="help")
        }


class ForwardCustomerDrawbackEmailTemplate(ForwardCustomerEditEmailTemplate):
    template = 'forward_customer_drawback'


class ForwardAdvisorEditEmailTemplate(PostOfficeEmailTemplate):
    template = 'forward_advisor_edit'

    def __init__(self, forward: FxForwardPosition):
        self.forward = forward
        super().__init__()

    def init_context_data(self):
        cashflow = self.forward.cashflow
        company = cashflow.account.company
        first_contact = company.companycontactorder_set.order_by('sort_order').first()
        self.context_data = {
            "customer_name": company.name,
            "cashflow_name": cashflow.name,
            "cashflow_id": cashflow.pk,
            "forward_id": self.forward.pk,
            "contact_name": f"{first_contact.user.first_name} {first_contact.user.last_name}",
            "contact_phone": first_contact.user.phone,
            "contact_email": first_contact.user.email,
        }


class ForwardAdvisorDrawbackEmailTemplate(ForwardAdvisorEditEmailTemplate):
    template = 'forward_advisor_drawback'


class NDFAdvisorEmailTemplate(ForwardAdvisorEditEmailTemplate):
    template = 'ndf_advisor'


class CreditDepositAdvisorEmailTemplate(PostOfficeEmailTemplate):
    template = 'credit_deposit_advisor'

    def __init__(self, company: Company):
        self.company = company
        super().__init__()

    def init_context_data(self):
        first_contact = self.company.companycontactorder_set.order_by('sort_order').first()
        self.context_data = {
            "customer_name": self.company.name,
            "contact_name": f"{first_contact.user.first_name} {first_contact.user.last_name}",
            "contact_phone": first_contact.user.phone,
            "contact_email": first_contact.user.email,
        }


class WalletTransferCompletedEmailTemplate(PostOfficeEmailTemplate):
    template = 'wallet_transfer_completed'

    def __init__(self, fxbalance: FXBalance):
        super().__init__()
        self.fxbalance = fxbalance

    def init_context_data(self):
        records = FXBalance.objects.filter(order_number=self.fxbalance.order_number)

        self.context_data = {
            "rate": 'rate TBD',
            "fee": 'N/A',
        }

        try:
            rec = records.get(amount__lt=0)
            self.context_data.update({
                "date": formats.date_format(rec.date, settings.SHORT_DATE_FORMAT),
                "account_from": rec.currency.mnemonic + ' Wallet (...' + str(rec.account_number)[-4:] + ')',
                "currency_from": rec.currency,
                "amount_from": abs(rec.amount),
            })
        except FXBalance.DoesNotExist:
            pass

        try:
            rec = records.get(amount__gt=0)
            self.context_data.update({
                "date": formats.date_format(rec.date, settings.SHORT_DATE_FORMAT),
                "account_to": rec.currency.mnemonic + ' Wallet (...' + str(rec.account_number)[-4:] + ')',
                "currency_to": rec.currency,
                "amount_to": abs(rec.amount),
            })
        except FXBalance.DoesNotExist:
            pass


class WalletTransferWaitingEmailTemplate(WalletTransferCompletedEmailTemplate):
    template = 'wallet_transfer_waiting'

    def init_context_data(self):
        super().init_context_data()
        self.context_data.update({
            "url": self.get_frontend_url(
                path='dashboard/wallets',
                query_params={
                    "order_number": self.fxbalance.order_number
                }
            )
        })


class PaymentWaitingEmailTemplate(WalletTransferCompletedEmailTemplate):
    template = 'payment_waiting'

    def init_context_data(self):
        super().init_context_data()
        self.context_data.update({
            "url": self.get_frontend_url(
                path='dashboard/wallets',
                query_params={
                    "order_number": self.fxbalance.order_number
                }
            ),
            "account_to": 'account_to TBD',
            "method": 'method TBD',
            "purpose": 'purpose TBD',
            "reference": 'reference TBD',
        })


class PaymentInitiatedEmailTemplate(PaymentWaitingEmailTemplate):
    template = 'payment_initiated'


class PaymentCompletedEmailTemplate(PaymentWaitingEmailTemplate):
    template = 'payment_completed'


class DepositWaitingEmailTemplate(WalletTransferCompletedEmailTemplate):
    template = 'deposit_waiting'

    def init_context_data(self):
        super().init_context_data()
        self.context_data.update({
            "url": self.get_frontend_url(
                path='dashboard/wallets',
                query_params={
                    "order_number": self.fxbalance.order_number
                }
            ),
            "account_from": 'account_from TBD',
            "method": 'method TBD',
            "reference": 'reference TBD',
            "fee": 'fee TBD',
        })


class DepositInitiatedEmailTemplate(DepositWaitingEmailTemplate):
    template = 'deposit_initiated'


class DepositReceivedEmailTemplate(DepositWaitingEmailTemplate):
    template = 'deposit_received'


class CreditDepositCustomerEmailTemplate(CreditDepositAdvisorEmailTemplate):
    template = 'credit_deposit_customer'

# ==================================

def to_html( table, df_styles=None ):

    if isinstance(table, dict):
        html_table = ''.join( '<tr><th>' + key + '</th><td>' + str(val) + '</td></tr>' for key, val in table.items() )
        html_table = f'<table>{html_table}</table>'
    elif isinstance(table, pd.DataFrame):
        df_styles = df_styles or {}
        html_table = table.to_html(**df_styles)
    else:
        print("WARN: unknown type", type(table))
        html_table = f'<table>{table}</table>'

    return html_table

class TradeConfirmationEmailTemplate(PostOfficeEmailTemplate):
    template = 'trade_confirmation'

    def __init__(self, context: dict, dict_table: dict):
        self.context_data = context
        self.context_data['table_content'] = to_html(dict_table)
        self.context_data['title'] = context.get('title') or 'TRADE CONFIRMATION'

        self.attachments = [
            PDFAttachmentTemplate('trade_confirmation_pdf')
        ]
        super().__init__()

    def init_context_data(self):
        required_keys = ['title', 'company', 'operation', 'order_id', 'date']
        for key in required_keys:
            assert key in self.context_data


class MarkToMarketEmailTemplate(PostOfficeEmailTemplate):
    template = 'mark_to_market'

    def __init__(self, context: dict, df_trades: pd.DataFrame):
        self.context_data = context
        self.context_data['table_content'] = to_html(df_trades)
        self.context_data['title'] = context.get('title') or 'MTM Statement'

        self.attachments = [
            PDFAttachmentTemplate('trade_confirmation_pdf','MTM-Statement.pdf')
        ]
        super().__init__()

    def init_context_data(self):
        required_keys = ['title', 'company', 'operation', 'order_id', 'date']
        for key in required_keys:
            assert key in self.context_data


class PaymentApprovalEmailTemplate(FileEmailTemplate):
    app = 'payment'

    def __init__(self, context_data:Dict):
        self.context_data = context_data
        super().__init__()

    def init_context_data(self):
        self.context_data['payment_link'] = self.get_frontend_url(
            path=self.context_data['url_path'],
            query_params=self.context_data['query_params'])


class PaymentApprovalRequestEmailTemplate(PaymentApprovalEmailTemplate):
    template = 'request_approval'
    subject = 'Payment: Approval Needed'


class PaymentApprovedRequestEmailTemplate(PaymentApprovalEmailTemplate):
    template = 'request_approved'
    subject = 'Payment: Request Approved'


EMAIL_APP_TEMPLATE_MAP = {
    'account': {
        'reset_password': ResetPasswordEmailTemplate,
        'invitation': InvitationEmailTemplate,
        'user_activation': UserActivationEmailTemplate,
        'company_join_request': CompanyJoinRequestEmailTemplate,
        'company_non_sellable_forward': CompanyNonSellableForwardEmailTemplate,
        'pending_approval': PendingApprovalEmailTemplate,
        'forward': ForwardEmailTemplate,
        'forward_customer_edit': ForwardCustomerEditEmailTemplate,
        'forward_customer_drawback': ForwardCustomerDrawbackEmailTemplate,
        'ndf_advisor': NDFAdvisorEmailTemplate,
        'forward_advisor_edit': ForwardAdvisorEditEmailTemplate,
        'forward_advisor_drawback': ForwardAdvisorDrawbackEmailTemplate,
        'credit_deposit_customer': CreditDepositCustomerEmailTemplate,
        'credit_deposit_advisor': CreditDepositAdvisorEmailTemplate,

        'wallet_transfer_completed': WalletTransferCompletedEmailTemplate,
        'wallet_transfer_waiting': WalletTransferWaitingEmailTemplate,

        'payment_initiated': PaymentInitiatedEmailTemplate,
        'payment_waiting': PaymentWaitingEmailTemplate,
        'payment_completed': PaymentCompletedEmailTemplate,

        'deposit_initiated': DepositInitiatedEmailTemplate,
        'deposit_waiting': DepositWaitingEmailTemplate,
        'deposit_received': DepositReceivedEmailTemplate,
    },
    'margin': {
        'margin_received': MarginReceivedEmailTemplate,
        'deposit_required': DepositRequiredEmailTemplate,
        'low_margin': LowMarginEmailTemplate
    },
    'billing': {
        "invoice": InvoiceEmailTemplate
    }
}
