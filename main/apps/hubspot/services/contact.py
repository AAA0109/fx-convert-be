from hubspot.crm.contacts import SimplePublicObjectInput, ApiException, SimplePublicObject, PublicObjectSearchRequest

from main.apps.account.models import User
from main.apps.hubspot.services.base import HubSpotBaseService


class HubSpotContactService(HubSpotBaseService):
    """
    Create a HubSpot Company, data dict should contain the following fields:
    {
      "company": "Pangea Technologies Inc.",
      "email": "suport@pangea.io",
      "firstname": "John",
      "lastname": "Doe",
      "phone": "(877) 929-0687",
      "website": "pangea.io"
    }
    """

    def create_contact(self, properties: dict) -> SimplePublicObject:
        try:
            object_input = SimplePublicObjectInput(properties=properties)
            return self.client.crm.contacts.basic_api.create(simple_public_object_input=object_input)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Get a HubSpot Contact by ID
    """

    def read_contact(self, contact_id: str) -> SimplePublicObject:
        try:
            return self.client.crm.contacts.basic_api.get_by_id(contact_id=contact_id)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Update a HubSpot Contact by contact_id, data dict should contain the following fields:
    {
      "company": "Pangea Technologies Inc.",
      "email": "suport@pangea.io",
      "firstname": "John",
      "lastname": "Doe",
      "phone": "(877) 929-0687",
      "website": "pangea.io"
    }
    """

    def update_contact(self, properties: dict, contact_id) -> SimplePublicObject:
        try:
            object_input = SimplePublicObjectInput(properties=properties)
            return self.client.crm.contacts.basic_api.update(simple_public_object_input=object_input,
                                                             contact_id=contact_id)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Delete a company by contact_id
    """

    def delete_contact(self, contact_id: str):
        try:
            return self.client.crm.contacts.basic_api.archive(contact_id=contact_id)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Create HubSpot Contact from account.User
    """

    def create_hs_contact_from_user(self, user: User):
        phone = None
        if user.phone is not None:
            phone = user.phone.as_e164
        properties = {
            "company": user.company.name,
            "email": user.email,
            "firstname": user.first_name,
            "lastname": user.last_name,
            "phone": phone
        }
        response = self.create_contact(properties)
        user.hs_contact_id = response.id
        user.save()
        return response

    """
    Get or create a HubSpot Contact by Email
    """

    def get_or_create_hs_contact_by_email(self, email: str, data: dict):
        filter_groups = [
            {
                "filters": [
                    {
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email
                    }
                ]
            }
        ]
        search_request = PublicObjectSearchRequest(filter_groups=filter_groups)
        try:
            response = self.client.crm.contacts.search_api.do_search(public_object_search_request=search_request)
            if response.total > 0:
                result = response.results[0]
                return result
            else:
                result = self.create_contact(data)
                return result

        except ApiException as e:
            self.log_and_raise_error(e)


