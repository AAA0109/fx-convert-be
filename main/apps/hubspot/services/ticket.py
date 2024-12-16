from django.conf import settings
from hubspot.crm.tickets import SimplePublicObjectInput, ApiException, SimplePublicObject
from main.apps.hubspot.services.base import HubSpotBaseService


class HubSpotTicketService(HubSpotBaseService):
    DEFAULT_PIPELINE = 0
    DEFAULT_PIPELINE_STAGE = 1
    DEFAULT_TICKET_PRIORITY = "MEDIUM"
    DEFAULT_TICKET_OWNER_ID = settings.HUBSPOT_TICKET_OWNER_ID

    """
    Create a HubSpot Ticket, data dict should contain the following fields:
    {
      "hs_pipeline": "1",
      "hs_pipeline_stage": "0",
      "hs_ticket_priority": "HIGH",
      "hubspot_owner_id": "123",
      "subject": "troubleshoot report",
      "content": "need help with report"
    }
    """

    def create_ticket(self, properties: dict) -> SimplePublicObject:
        try:
            object_input = SimplePublicObjectInput(properties=properties)
            return self.client.crm.tickets.basic_api.create(simple_public_object_input=object_input)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Get a HubSpot Ticket by ID
    """

    def read_ticket(self, ticket_id: str) -> SimplePublicObject:
        try:
            return self.client.crm.tickets.basic_api.get_by_id(ticket_id=ticket_id)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Update a HubSpot Ticket, data dict should contain the following fields:
    {
      "hs_pipeline": "1",
      "hs_pipeline_stage": "0",
      "hs_ticket_priority": "HIGH",
      "hubspot_owner_id": "123",
      "subject": "troubleshoot report",
      "content": "need help with report\nadditional issues"
    }
    """

    def update_ticket(self, properties: dict, ticket_id: str):
        try:
            object_input = SimplePublicObjectInput(properties=properties)
            return self.client.crm.tickets.basic_api.update(simple_public_object_input=object_input,
                                                            ticket_id=ticket_id)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Delete a ticket by ticket_id
    """

    def delete_ticket(self, ticket_id: str):
        try:
            return self.client.crm.tickets.basic_api.archive(ticket_id=ticket_id)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Associate Ticket with Contact
    """

    def associate_ticket_with_contact(self, ticket_id: str, contact_id: str):
        try:
            return self.client.crm.tickets.associations_api.create(ticket_id=ticket_id, to_object_type='contact',
                                                                   to_object_id=contact_id,
                                                                   association_type='ticket_to_contact')
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Associate Ticket with Contact
    """

    def associate_ticket_with_company(self, ticket_id: str, company_id: str):
        try:
            return self.client.crm.tickets.associations_api.create(ticket_id=ticket_id, to_object_type='company',
                                                                   to_object_id=company_id,
                                                                   association_type='ticket_to_company')
        except ApiException as e:
            self.log_and_raise_error(e)
