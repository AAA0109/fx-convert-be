from hubspot.crm.companies import SimplePublicObjectInput, ApiException, SimplePublicObject

from main.apps.account.models import Company
from main.apps.hubspot.services.base import HubSpotBaseService


class HubSpotCompanyService(HubSpotBaseService):
    """
    Create a HubSpot Company, data dict should contain the following fields:
    {
        "city": "San Diego",
        "industry": "FinTech",
        "name": "Pangea Technologies",
        "phone": "(877) 929-0687",
        "state": "California"
    }
    """

    def create_company(self, properties: dict) -> SimplePublicObject:
        try:
            object_input = SimplePublicObjectInput(properties=properties)
            return self.client.crm.companies.basic_api.create(simple_public_object_input=object_input)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Get a HubSpot Company by ID
    """

    def read_company(self, company_id: str) -> SimplePublicObject:
        try:
            return self.client.crm.companies.basic_api.get_by_id(company_id=company_id)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Update a HubSpot Company by company_id, data dict should contain the following fields:
    {
        "city": "San Diego",
        "industry": "FinTech",
        "name": "Pangea Technologies",
        "phone": "(877) 929-0687",
        "state": "California"
    }
    """

    def update_company(self, properties: dict, company_id: str) -> SimplePublicObject:
        try:
            object_input = SimplePublicObjectInput(properties=properties)
            return self.client.crm.companies.basic_api.update(simple_public_object_input=object_input,
                                                              company_id=company_id)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Delete a company by company_id
    """

    def delete_company(self, company_id: str) -> None:
        try:
            return self.client.crm.companies.basic_api.archive(company_id=company_id)
        except ApiException as e:
            self.log_and_raise_error(e)

    """
    Create HubSpot Company from account.Company
    """

    def create_hs_company_from_company(self, company: Company):
        phone = None
        if company.phone is not None:
            phone = company.phone.as_e164
        properties = {
            "city": company.city,
            "name": company.name,
            "phone": phone,
            "state": company.state
        }
        response = self.create_company(properties)
        company.hs_company_id = response.id
        company.save()
        return response
