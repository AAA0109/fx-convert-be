import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse, NoReverseMatch
from rest_framework import status
from rest_framework.test import APIClient

from main.apps.account.models import Company
from main.apps.currency.models import Currency
from main.apps.settlement.models import Beneficiary

User = get_user_model()


class BeneficiaryViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.currency = Currency.objects.create(mnemonic='USD')
        self.company1 = Company.objects.create(name="Company 1", currency=self.currency)
        self.company2 = Company.objects.create(name="Company 2", currency=self.currency)
        self.user1 = User.objects.create_user(email='user1@test.dev', password='12345', company=self.company1)
        self.user2 = User.objects.create_user(email='user2@test.dev', password='12345', company=self.company2)

        # Create test beneficiaries
        self.beneficiary1 = Beneficiary.objects.create(
            beneficiary_id=uuid.uuid4(),
            beneficiary_name="Test Beneficiary 1",
            beneficiary_alias="test-alias-1",
            company=self.company1
        )
        self.beneficiary2 = Beneficiary.objects.create(
            beneficiary_id=uuid.uuid4(),
            beneficiary_name="Test Beneficiary 2",
            beneficiary_alias="test-alias-2",
            company=self.company1
        )
        self.beneficiary3 = Beneficiary.objects.create(
            beneficiary_id=uuid.uuid4(),
            beneficiary_name="Test Beneficiary 3",
            beneficiary_alias="test-alias-1",  # Same alias as beneficiary1, but different company
            company=self.company2
        )

    def test_retrieve_by_uuid(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('v2:settlement:beneficiary-detail',
                      kwargs={'pk': self.beneficiary1.beneficiary_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['beneficiary_id'], str(self.beneficiary1.beneficiary_id))

    def test_retrieve_by_alias(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('v2:settlement:beneficiary-detail',
                      kwargs={'pk': self.beneficiary1.beneficiary_alias})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['beneficiary_alias'], self.beneficiary1.beneficiary_alias)

    def test_retrieve_invalid_uuid(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('v2:settlement:beneficiary-detail', kwargs={'pk': 'invalid-uuid'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_non_existent_alias(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('v2:settlement:beneficiary-detail', kwargs={'pk': 'non-existent-alias'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_empty_pk(self):
        self.client.force_authenticate(user=self.user1)
        try:
            url = reverse('v2:settlement:beneficiary-detail', kwargs={'pk': ''})
        except NoReverseMatch:
            # If reversing the URL fails, the test passes as expected
            return

        # If we get here, it means the URL was successfully reversed, which is unexpected
        self.fail("URL should not be reversible with an empty pk")

    def test_update_by_uuid(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('v2:settlement:beneficiary-detail',
                      kwargs={'pk': self.beneficiary1.beneficiary_id})
        data = {'beneficiary_name': 'Updated Name'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.beneficiary1.refresh_from_db()
        self.assertEqual(self.beneficiary1.beneficiary_name, 'Updated Name')

    def test_update_by_alias(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('v2:settlement:beneficiary-detail',
                      kwargs={'pk': self.beneficiary1.beneficiary_alias})
        data = {'beneficiary_name': 'Updated By Alias'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.beneficiary1.refresh_from_db()
        self.assertEqual(self.beneficiary1.beneficiary_name, 'Updated By Alias')

    def test_delete_by_uuid(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('v2:settlement:beneficiary-detail',
                      kwargs={'pk': self.beneficiary1.beneficiary_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Beneficiary.objects.filter(id=self.beneficiary1.id).exists())

    def test_delete_by_alias(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('v2:settlement:beneficiary-detail',
                      kwargs={'pk': self.beneficiary2.beneficiary_alias})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Beneficiary.objects.filter(id=self.beneficiary2.id).exists())

    def test_retrieve_with_null_alias(self):
        self.client.force_authenticate(user=self.user1)
        beneficiary_no_alias = Beneficiary.objects.create(
            beneficiary_id=uuid.uuid4(),
            beneficiary_name="Test Beneficiary No Alias",
            company=self.company1
        )
        url = reverse('v2:settlement:beneficiary-detail',
                      kwargs={'pk': beneficiary_no_alias.beneficiary_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['beneficiary_id'], str(beneficiary_no_alias.beneficiary_id))

    def test_create_duplicate_alias(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('v2:settlement:beneficiary-list')
        data = {
            'beneficiary_name': 'Duplicate Alias',
            'beneficiary_alias': self.beneficiary1.beneficiary_alias
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_to_existing_alias_same_company(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('v2:settlement:beneficiary-detail',
                      kwargs={'pk': self.beneficiary2.beneficiary_id})
        data = {'beneficiary_alias': self.beneficiary1.beneficiary_alias}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_to_existing_alias_different_company(self):
        self.client.force_authenticate(user=self.user2)
        url = reverse('v2:settlement:beneficiary-detail',
                      kwargs={'pk': self.beneficiary3.beneficiary_id})
        data = {'beneficiary_alias': 'test-alias-2'}  # This alias exists in company1, but not in company2
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
