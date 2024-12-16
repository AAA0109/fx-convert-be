from typing import List

from celery import shared_task
from django.conf import settings
from django_rest_passwordreset.models import ResetPasswordToken
from post_office.mail import send as send_mail

from main.apps.account.models import User, Company
from main.apps.notification.services.email.templates import (
    BaseEmailTemplate,
    ResetPasswordEmailTemplate,
    InvitationEmailTemplate,
    UserActivationEmailTemplate, InvoiceEmailTemplate, MarkToMarketEmailTemplate, TradeConfirmationEmailTemplate
)


class EmailService:
    def __init__(self, recipient_list=[], cc=[], bcc=[], subject=None, body=None):
        self.email_template = None # type: BaseEmailTemplate
        self.from_email = settings.DEFAULT_FROM_EMAIL
        self.recipient_list = recipient_list
        self.cc = cc
        self.bcc = bcc
        self.subject = subject
        self.body = body

    def set_from_email(self, from_email: str):
        self.from_email = from_email
        self.recipient_list = from_email

    def set_email_template(self, email_template: BaseEmailTemplate):
        self.email_template = email_template

    def get_recipient_list(self):
        return self.recipient_list

    def set_recipient_list(self, recipient_list: List = []):
        self.recipient_list = recipient_list

    def add_to_recipient_list(self, email):
        self.recipient_list.append(email)

    def render_and_send(self):
        # @todo refactory all the class inherited from FileEmailTemplate and use: language, template and context

        attachments = None

        if self.body:
            txt_message = self.body
            html_message = self.body

        if self.email_template:
            if not self.body:
                txt_message = self.email_template.render(format='txt')
                html_message = self.email_template.render(format='html')
            attachments = self.email_template.get_attachments()
        else:
            raise ValueError

        subject = self.subject or self.email_template.subject
        cc = self.cc
        bcc = self.bcc

        send_mail(
            recipients=self.get_recipient_list(),
            sender=self.from_email,
            subject=subject,
            cc=cc,
            bcc=bcc,
            priority='now',
            message=txt_message,
            html_message=html_message,
            attachments=attachments
        )


def send_email_template(template: BaseEmailTemplate, recipient_list: List, cc: List=[], bcc: List=[], subject: str=None, body: str=None):
    email_service = EmailService( cc=cc, bcc=bcc, subject=subject, body=body )
    email_service.set_email_template(template)
    email_service.set_recipient_list(recipient_list)
    email_service.render_and_send()

# ===========================

@shared_task(serializer='json')
def send_email_async(*args, **kwargs):
    return send_email_template(*args, **kwargs)

@shared_task(serializer='json')
def send_email( template: str, context, payload, recipients, **kwargs):
    template_mapping = {
        'mtm': MarkToMarketEmailTemplate,
        'trade_confirm': TradeConfirmationEmailTemplate
    }
    template_obj = template_mapping[template]
    # this action should be moved to a celery job
    template = template_obj(context, payload)
    send_email_template(template, recipients, **kwargs)

# ===========================

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


def send_invoice_email(company: Company):
    template = InvoiceEmailTemplate(
        company=company
    )
    send_email_template(template=template, recipient_list=[company.account_owner.email])
