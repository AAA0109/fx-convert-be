import logging
import time
import unittest

from django.conf import settings
from django.test import TestCase

from main.apps.hubspot.services.company import HubSpotCompanyService

from main.apps.hubspot.services.contact import HubSpotContactService


class HubSpotTestCase(TestCase):
    created_company_ids = []
    created_contact_ids = []

    def setUp(self):
        self.company_data = {
            "city": "San Diego",
            "industry": "FinTech",
            "name": "Pangea Technologies",
            "phone": "(877) 929-0687",
            "state": "California"
        }
        self.contact_data = {
            "company": "Pangea Technologies Inc.",
            "email": "suport@pangea.io",
            "firstname": "John",
            "lastname": "Doe",
            "phone": "(877) 929-0687",
            "website": "pangea.io"
        }
        self.get_or_create_contact_data = {
            "company": "Pangea Technologies Inc.",
            "email": "suport+1@pangea.io",
            "firstname": "John",
            "lastname": "Doe",
            "phone": "(877) 929-0687",
            "website": "pangea.io"
        }
        self.hs_company_service = HubSpotCompanyService()
        self.hs_contact_service = HubSpotContactService()

    def tearDown(self):
        for company_id in self.created_company_ids:
            self.hs_company_service.delete_company(company_id)
        for contact_id in self.created_contact_ids:
            self.hs_contact_service.delete_contact(contact_id)

    @unittest.skipIf(not settings.HUBSPOT_RUN_TESTS, "Only run if HUBSPOT_RUN_TESTS is set to True")
    def test_create_company(self):
        response = self.hs_company_service.create_company(self.company_data)
        self.created_company_ids.append(response.id)
        self.assertIsInstance(response.id, str)

    @unittest.skipIf(not settings.HUBSPOT_RUN_TESTS, "Only run if HUBSPOT_RUN_TESTS is set to True")
    def test_update_company(self):
        response = self.hs_company_service.create_company(self.company_data)
        self.created_company_ids.append(response.id)
        data = {
            "city": "Las Vegas"
        }
        response = self.hs_company_service.update_company(properties=data, company_id=response.id)
        self.assertEqual(response.properties['city'], 'Las Vegas')

    @unittest.skipIf(not settings.HUBSPOT_RUN_TESTS, "Only run if HUBSPOT_RUN_TESTS is set to True")
    def test_delete_company(self):
        if len(self.created_company_ids) > 0:
            company_id = self.created_company_ids.pop(0)
            response = self.hs_company_service.delete_company(company_id)
        else:
            response = self.hs_company_service.create_company(self.company_data)
            response = self.hs_company_service.delete_company(response.id)
        self.assertIsNone(response)

    @unittest.skipIf(not settings.HUBSPOT_RUN_TESTS, "Only run if HUBSPOT_RUN_TESTS is set to True")
    def test_create_contact(self):
        response = self.hs_contact_service.create_contact(self.contact_data)
        self.created_contact_ids.append(response.id)
        self.assertIsInstance(response.id, str)

    @unittest.skipIf(not settings.HUBSPOT_RUN_TESTS, "Only run if HUBSPOT_RUN_TESTS is set to True")
    def test_update_contact(self):
        response = self.hs_contact_service.create_contact(self.contact_data)
        self.created_contact_ids.append(response.id)
        data = {
            "firstname": "Brian"
        }
        response = self.hs_contact_service.update_contact(properties=data, contact_id=response.id)
        self.assertEqual(response.properties['firstname'], 'Brian')

    @unittest.skipIf(not settings.HUBSPOT_RUN_TESTS, "Only run if HUBSPOT_RUN_TESTS is set to True")
    def test_delete_contact(self):
        if len(self.created_contact_ids) > 0:
            contact_id = self.created_contact_ids.pop(0)
            response = self.hs_contact_service.delete_contact(contact_id)
        else:
            response = self.hs_contact_service.create_contact(self.contact_data)
            response = self.hs_contact_service.delete_contact(response.id)
        self.assertIsNone(response)

    @unittest.skipIf(not settings.HUBSPOT_RUN_TESTS, "Only run if HUBSPOT_RUN_TESTS is set to True")
    def test_get_or_create_contact_by_email(self):
        # Test create
        logging.info("testing create hubspot contact")
        response = self.hs_contact_service.get_or_create_hs_contact_by_email(self.get_or_create_contact_data["email"],
                                                                             self.get_or_create_contact_data)
        create_id = response.id

        self.created_contact_ids.append(response.id)
        tries = 0
        while tries < 5:
            try:
                # Test search
                logging.info("testing search hubspot contact")
                response = self.hs_contact_service.get_or_create_hs_contact_by_email(
                    self.get_or_create_contact_data["email"],
                    self.get_or_create_contact_data)
                search_id = response.id
                self.assertEqual(create_id, search_id)
                break
            except Exception as e:
                tries += 1
                logging.error(f"Encountered hubspot error when calling get_or_create, sleeping for {tries} seconds")
                time.sleep(tries)
