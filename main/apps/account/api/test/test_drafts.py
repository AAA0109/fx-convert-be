from datetime import datetime
from typing import Optional

import pytz
from django.urls import reverse
from rest_framework import status

from main.apps.account.api.test import BaseTestCase
from hdlib.DateTime.Date import Date

from main.apps.account.models import DraftCashFlow, InstallmentCashflow


class DraftTest(BaseTestCase):

    def test_create_draft(self):
        response = self.create_draft(
            name='Test Draft',
            cny=self.usd.mnemonic,
            amount=100.0,
            date=Date(2018, 1, 1),
            end_date=Date(2020, 1, 1),
            periodicity='1M',
            calendar='NULL_CALENDAR',
            description='Test draft',
            installment_id=None
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DraftCashFlow.objects.count(), 1)
        draft = DraftCashFlow.objects.first()
        self.assertEqual(draft.company, self.company)
        self.assertEqual(draft.name, 'Test Draft')
        self.assertEqual(draft.currency.mnemonic, self.usd.mnemonic)
        self.assertEqual(draft.amount, 100.0)
        self.assertEqual(draft.date, datetime(2018, 1, 1, tzinfo=pytz.UTC))
        self.assertEqual(draft.end_date, datetime(2020, 1, 1, tzinfo=pytz.UTC))
        self.assertEqual(draft.periodicity, '1M')
        self.assertEqual(draft.calendar, 'NULL_CALENDAR')
        self.assertEqual(draft.description, 'Test draft')
        self.assertEqual(draft.action, DraftCashFlow.Action.CREATE)

    def test_create_draft_with_invalid_calendar(self):
        response = self.create_draft(
            name='Test Draft',
            cny=self.usd.mnemonic,
            amount=100.0,
            date=Date(2018, 1, 1),
            end_date=Date(2020, 1, 1),
            periodicity='1M',
            calendar='INVALID_CALENDAR',
            description='Test draft',
            installment_id=None
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(DraftCashFlow.objects.count(), 0)

    def test_get_drafts(self):
        self.create_draft(
            name='Test Draft',
            cny=self.usd.mnemonic,
            amount=100.0,
            date=Date(2018, 1, 1),
            end_date=Date(2020, 1, 1),
            periodicity='1M',
            calendar='NULL_CALENDAR',
            description='Test draft',
            installment_id=None
        )
        self.create_draft(
            name='Test Draft 2',
            cny=self.usd.mnemonic,
            amount=100.0,
            date=Date(2018, 1, 1),
            end_date=Date(2020, 1, 1),
            periodicity='1M',
            calendar='NULL_CALENDAR',
            description='Test draft',
            installment_id=None
        )
        response = self.client.get(reverse('main:account:drafts-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['name'], 'Test Draft')
        self.assertEqual(response.data['results'][1]['name'], 'Test Draft 2')

    def test_update_draft(self):
        draft = self.create_draft(
            name='Test Draft',
            cny=self.usd.mnemonic,
            amount=100.0,
            date=Date(2018, 1, 1),
            end_date=Date(2020, 1, 1),
            periodicity='1M',
            calendar='NULL_CALENDAR',
            description='Test draft',
            installment_id=None
        )
        self.assertEqual(draft.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DraftCashFlow.objects.count(), 1)
        draft = DraftCashFlow.objects.first()

        response = self.update_draft(
            draft.id,
            name='Test Draft Updated',
            cny=self.usd.mnemonic,
            amount=-200.0,
            date=Date(2018, 1, 1),
            end_date=Date(2020, 1, 1),
            periodicity='1M',
            calendar='NULL_CALENDAR',
            description='Test draft updated',
            installment_id=None
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(DraftCashFlow.objects.count(), 1)
        draft = DraftCashFlow.objects.first()
        self.assertEqual(draft.company, self.company)
        self.assertEqual(draft.name, 'Test Draft Updated')
        self.assertEqual(draft.currency.mnemonic, self.usd.mnemonic)
        self.assertEqual(draft.amount, -200.0)
        self.assertEqual(draft.action, DraftCashFlow.Action.UPDATE)

    def test_delete_cashflow(self):
        draft = self.create_draft(
            name='Test Draft',
            cny=self.usd.mnemonic,
            amount=100.0,
            date=Date(2018, 1, 1),
            end_date=Date(2020, 1, 1),
            periodicity='1M',
            calendar='NULL_CALENDAR',
            description='Test draft',
            installment_id=None
        )
        self.assertEqual(draft.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DraftCashFlow.objects.count(), 1)
        draft = DraftCashFlow.objects.first()

        response = self.client.delete(reverse('main:account:drafts-detail', args=[draft.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(DraftCashFlow.objects.count(), 0)


    def test_draft_with_installment(self):
        installment = InstallmentCashflow.create_installment(company_id=self.company.id, installment_name='Test Installment')
        draft = self.create_draft(
            name='Test Draft',
            cny=self.usd.mnemonic,
            amount=100.0,
            date=Date(2018, 1, 1),
            end_date=Date(2020, 1, 1),
            periodicity='1M',
            calendar='NULL_CALENDAR',
            description='Test draft',
            installment_id=installment.id)
        self.assertEqual(draft.status_code, status.HTTP_201_CREATED)
        self.assertEqual(draft.data['installment_id'], installment.id)


    def test_update_draft_with_installment(self):
        installment = InstallmentCashflow.create_installment(company_id=self.company.id, installment_name='Test Installment')
        draft = self.create_draft(
            name='Test Draft',
            cny=self.usd.mnemonic,
            amount=100.0,
            date=Date(2018, 1, 1),
            end_date=Date(2020, 1, 1),
            periodicity='1M',
            calendar='NULL_CALENDAR',
            description='Test draft',
            installment_id=None
        )
        self.assertEqual(draft.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DraftCashFlow.objects.count(), 1)
        draft = DraftCashFlow.objects.first()

        response = self.update_draft(
            draft.id,
            name='Test Draft Updated',
            cny=self.usd.mnemonic,
            amount=-200.0,
            date=Date(2018, 1, 1),
            end_date=Date(2020, 1, 1),
            periodicity='1M',
            calendar='NULL_CALENDAR',
            description='Test draft updated',
            installment_id=installment.id
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['installment_id'], installment.id)

    def create_draft(self,
                     name: str,
                     cny: str,
                     amount: float,
                     date: Date,
                     end_date: Date,
                     periodicity: str,
                     calendar: str,
                     description: str,
                     installment_id: Optional[int]):
        req = {
            'name': name,
            'currency': cny,
            'amount': amount,
            'date': date.to_str(fmt='%Y-%m-%dT%H:%M:%SZ'),
            'end_date': end_date.to_str(fmt='%Y-%m-%dT%H:%M:%SZ'),
            'periodicity': periodicity,
            'calendar': calendar,
            'description': description,
            'action': 'CREATE'
        }
        if installment_id:
            req['installment_id'] = installment_id
        return self.client.post(reverse('main:account:drafts-list'), req)

    def update_draft(self,
                     id: int,
                     name: str,
                     cny: str,
                     amount: float,
                     date: Date,
                     end_date: Date,
                     periodicity: str,
                     calendar: str,
                     description: str,
                     installment_id : Optional[int]):
        req = {
            'name': name,
            'currency': cny,
            'amount': amount,
            'date': date.to_str(fmt='%Y-%m-%dT%H:%M:%SZ'),
            'end_date': end_date.to_str(fmt='%Y-%m-%dT%H:%M:%SZ'),
            'periodicity': periodicity,
            'calendar': calendar,
            'description': description,
            'action': 'UPDATE'
        }

        if installment_id:
            req['installment_id'] = installment_id

        return self.client.put(reverse('main:account:drafts-detail', args=[id]),req)
