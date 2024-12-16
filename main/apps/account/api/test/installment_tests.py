import unittest
from datetime import datetime

from django.urls import reverse
from rest_framework import status

from main.apps.account.api.test import BaseTestCase
from main.apps.account.models import CashFlow, InstallmentCashflow

from hdlib.DateTime.Date import Date


class InstallmentCashflowTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.create_default_account()

    def test_create_installment(self):
        response = self.create_installment('Test Installment')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InstallmentCashflow.objects.count(), 1)
        installment = InstallmentCashflow.objects.first()
        self.assertEqual(installment.company, self.company)
        self.assertEqual(installment.installment_name, "Test Installment")

    def test_get_installments(self):
        response = self.create_installment('Test Installment')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(reverse('main:account:installments-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['installment_name'], "Test Installment")

    def test_get_installment(self):
        response = self.create_installment('Test Installment')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        installment = InstallmentCashflow.objects.first()
        response = self.client.get(reverse('main:account:installments-detail', args=[installment.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['installment_name'], "Test Installment")

    def test_update_installment(self):
        response = self.create_installment('Test Installment')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        installment = InstallmentCashflow.objects.first()
        response = self.client.put(reverse('main:account:installments-detail', args=[installment.id]),
                                   data={'installment_name': 'Test Installment 2'},
                                   format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['installment_name'], "Test Installment 2")

    def test_delete_installment(self):
        response = self.create_installment('Test Installment')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        installment_id = response.data['id']
        installment = InstallmentCashflow.objects.get(pk=installment_id)
        self.add_cashflows_to_installment(installment)
        response = self.client.delete(reverse('main:account:installments-detail', args=[installment.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        cashflows = installment.cashflow_set.all()
        for cashflow in cashflows:
            self.assertEqual(cashflow.status, CashFlow.CashflowStatus.PENDING_DEACTIVATION)

    def create_installment(self, name: str):
        response = self.client.post(reverse('main:account:installments-list', ),
                                    data={'installment_name': name},
                                    format='json')
        return response

    def add_cashflows_to_installment(self, installment: InstallmentCashflow):
        data = []
        for cf_id in range(5):
            data.append(CashFlow(
                account=self.account,
                name=f"cashflow {cf_id}",
                currency=self.usd,
                amount="10000",
                date=Date(2021, 7, 1, tzinfo=Date.timezone_UTC),
                description=f"Test Description {cf_id}",
                installment=installment,
                status=CashFlow.CashflowStatus.ACTIVE
            ))
        CashFlow.objects.bulk_create(data)


if __name__ == '__main__':
    unittest.main()
