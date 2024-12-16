from django.db.models.signals import post_save

from main.apps.account.models import Company
from main.apps.account.models.test.base import BaseTestCase
from main.apps.account.models.user import User
from main.apps.currency.models import Currency


class UserTestCase(BaseTestCase):

    def setUp(self) -> None:

        _, self.usd = Currency.create_currency(symbol="$", mnemonic="USD", name="US Dollar")
        self.company = Company.create_company(name='Test Company', currency=self.usd)
        self.user = User.objects.create_user("email@example.com", "password")
        self.user.company = self.company
        self.user.save()

    def tearDown(self) -> None:
        self.usd.delete()
        self.user.delete()
        if self.company and self.company.id: self.company.delete()


    def test_user_not_deleted_when_company_is_deleted(self):
        """
        Tests that when a company is deleted, the user's company field is set to null.
        """
        company_id = self.company.id
        self.user.refresh_from_db()
        self.assertEqual(self.user.company_id, company_id)

        self.company.delete()

        self.user.refresh_from_db()
        self.assertIsNone(self.user.company)
