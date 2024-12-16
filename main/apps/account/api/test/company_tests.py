import unittest

from django.db.models.signals import post_save
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

import main.libs.pubsub.publisher as pubsub
from main.apps.account.models import Company, User
from main.apps.currency.models import Currency


class CompanyTestCase(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        pubsub.init_null({})

    def setUp(self):
        _, self.usd = Currency.create_currency(symbol="$", mnemonic="USD", name="US Dollar")
        self.user = User.objects.create_user("email@example.com", "password")
        self.login_jwt(email="email@example.com", password="password")


    def test_create_company(self):
        response = self.client.post(reverse('main:account:company-list'), {
            'name': 'Test Company',
            'currency': 'USD'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Company.objects.get().name, 'Test Company')
        self.assertEqual(Company.objects.get().currency, self.usd)
        self.assertEqual(Company.objects.get().status, Company.CompanyStatus.ACTIVE)
        user = User.objects.get(email="email@example.com")
        self.assertEqual(user.company, Company.objects.get())

    def test_create_company_with_invalid_currency(self):
        response = self.client.post(reverse('main:account:company-list'), {
            'name': 'Test Company',
            'currency': 'INVALID'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Company.objects.count(), 0)

    def test_get_company(self):
        response = self.client.post(reverse('main:account:company-list'), {
            'name': 'Test Company',
            'currency': 'USD'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(reverse('main:account:company-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        response_data = response.data[0]
        self.assertEqual(response_data['name'], 'Test Company')
        self.assertEqual(response_data['currency'], 'USD')
        self.assertEqual(response_data['status'], 'Active')

    def test_deactivate_company(self):
        response = self.client.post(reverse('main:account:company-list'), {
            'name': 'Test Company',
            'currency': 'USD'})
        company_id = response.data['id']
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.put(reverse('main:account:company-deactivate'))
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        company = Company.objects.get(pk=company_id)
        self.assertEqual(company.status, Company.CompanyStatus.DEACTIVATION_PENDING)

    def login_jwt(self, email, password):
        token_url = reverse('main:auth:token_obtain_pair')
        response = self.client.post(token_url, {
            "email": email,
            "password": password
        }, format="json")
        if response.status_code == status.HTTP_200_OK:
            token = response.json()
            self.access_token = token['access']
            self.refresh_token = token['refresh']
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        return response

if __name__ == '__main__':
    unittest.main()
