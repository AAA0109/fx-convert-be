import json
import logging
import re

from hubspot.crm.companies import ApiException as CompaniesApiException
from hubspot.crm.contacts import ApiException as ContactsApiException
from hubspot.crm.tickets.exceptions import ApiException as TicketApiException
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from main.apps.hubspot.services.company import HubSpotCompanyService
from main.apps.hubspot.services.contact import HubSpotContactService
from main.apps.hubspot.services.ticket import HubSpotTicketService

logger = logging.getLogger(__name__)


class SendAuthenticatedSupportMessageSerializer(serializers.Serializer):
    subject = serializers.CharField(allow_null=True)
    message = serializers.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hs_company_service = HubSpotCompanyService()
        self.hs_contact_service = HubSpotContactService()
        self.hs_ticket_service = HubSpotTicketService()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        hs_company_id = None
        hs_contact_id = None
        if validated_data['subject'] is None:
            validated_data['subject'] = "Prime support ticket"
        user = self.context['user']
        if user.hs_contact_id is None:
            try:
                response = self.hs_contact_service.create_hs_contact_from_user(user)
                hs_contact_id = response.id
            except ContactsApiException as e:
                logger.error(e.body)
                body = json.loads(e.body)
                if body['category'] == 'CONFLICT':
                    regex = r"Contact already exists. Existing ID: (?P<contact_id>[0-9]+)"
                    matches = re.match(regex, body['message'])
                    if matches is not None:
                        match_dict = matches.groupdict()
                        hs_contact_id = match_dict['contact_id']
        else:
            hs_contact_id = user.hs_contact_id

        if user.company.hs_company_id is None:
            try:
                response = self.hs_company_service.create_hs_company_from_company(user.company)
                hs_company_id = response.id
            except CompaniesApiException as e:
                logger.error(e.body)
        else:
            hs_company_id = user.company.hs_company_id

        ticket_data = {
            "subject": validated_data['subject'],
            "content": validated_data['message'],
            "hs_pipeline": HubSpotTicketService.DEFAULT_PIPELINE,
            "hs_pipeline_stage": HubSpotTicketService.DEFAULT_PIPELINE_STAGE,
            "hs_ticket_priority": HubSpotTicketService.DEFAULT_TICKET_PRIORITY,
            "hubspot_owner_id": HubSpotTicketService.DEFAULT_TICKET_OWNER_ID
        }

        try:
            ticket = self.hs_ticket_service.create_ticket(ticket_data)
            self.hs_ticket_service.associate_ticket_with_company(ticket_id=ticket.id, company_id=hs_company_id)
            self.hs_ticket_service.associate_ticket_with_contact(ticket_id=ticket.id, contact_id=hs_contact_id)
        except ContactsApiException as e:
            logger.error(e.body)
        except TicketApiException as e:
            logger.error(e.body)

        return validated_data


class SendGeneralSupportMessageSerializer(serializers.Serializer):
    firstname = serializers.CharField()
    lastname = serializers.CharField()
    subject = serializers.CharField()
    message = serializers.CharField()
    email = serializers.EmailField()
    phone = PhoneNumberField()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hs_company_service = HubSpotCompanyService()
        self.hs_contact_service = HubSpotContactService()
        self.hs_ticket_service = HubSpotTicketService()

    def create(self, validated_data):
        hs_contact_id = None
        if validated_data['subject'] is None:
            validated_data['subject'] = 'Prime general support ticket'
        try:
            contact_data = {
                "firstname": validated_data['firstname'],
                "lastname": validated_data['lastname'],
                "phone": validated_data['phone'].as_e164,
                "email": validated_data['email']
            }
            response = self.hs_contact_service.get_or_create_hs_contact_by_email(validated_data['email'], contact_data)
            hs_contact_id = response.id
        except ContactsApiException as e:
            logger.error(e.body)

        ticket_data = {
            "subject": validated_data["subject"],
            "content": validated_data["message"],
            "hs_pipeline": HubSpotTicketService.DEFAULT_PIPELINE,
            "hs_pipeline_stage": HubSpotTicketService.DEFAULT_PIPELINE_STAGE,
            "hs_ticket_priority": HubSpotTicketService.DEFAULT_TICKET_PRIORITY,
            "hubspot_owner_id": HubSpotTicketService.DEFAULT_TICKET_OWNER_ID
        }

        try:
            ticket = self.hs_ticket_service.create_ticket(ticket_data)
            self.hs_ticket_service.associate_ticket_with_contact(ticket_id=ticket.id, contact_id=hs_contact_id)
        except ContactsApiException as e:
            logger.error(e.body)
        except TicketApiException as e:
            logger.error(e.body)

        return validated_data

