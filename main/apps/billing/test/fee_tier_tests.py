import unittest

from main.apps.account.models.test.base import BaseTestCase
from main.apps.billing.models.fee_tier import FeeTier


class FeeScheduleTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_maintenance_fee_lifecycle(self):
        # Add an initial tier at zero
        FeeTier.create_tier(tier_from=0., company=self.company1, new_cash_fee_rate=0.0001, aum_fee_rate=0.01)

        for aum_level in (0., 100, 10000):
            tier = FeeTier.get_tier_for_aum_level(aum_level=aum_level, company=self.company1)
            self.assertEqual(tier.new_cash_fee_rate, 0.0001)
            self.assertEqual(tier.aum_fee_rate, 0.01)

        # Add a level above zero
        FeeTier.create_tier(tier_from=1000., company=self.company1, new_cash_fee_rate=0.0002, aum_fee_rate=0.02)

        for aum_level in (0., 100, 999.99):
            tier = FeeTier.get_tier_for_aum_level(aum_level=aum_level, company=self.company1)
            self.assertEqual(tier.new_cash_fee_rate, 0.0001)
            self.assertEqual(tier.aum_fee_rate, 0.01)

        for aum_level in (1000., 2000., 10000.):
            tier = FeeTier.get_tier_for_aum_level(aum_level=aum_level, company=self.company1)
            self.assertEqual(tier.new_cash_fee_rate, 0.0002)
            self.assertEqual(tier.aum_fee_rate, 0.02)

        # Add a level above that level
        FeeTier.create_tier(tier_from=10000.01, company=self.company1, new_cash_fee_rate=0.0003, aum_fee_rate=0.03)

        for aum_level in (0., 100, 999.99):
            tier = FeeTier.get_tier_for_aum_level(aum_level=aum_level, company=self.company1)
            self.assertEqual(tier.new_cash_fee_rate, 0.0001)
            self.assertEqual(tier.aum_fee_rate, 0.01)

        for aum_level in (1000., 2000., 10000.):
            tier = FeeTier.get_tier_for_aum_level(aum_level=aum_level, company=self.company1)
            self.assertEqual(tier.new_cash_fee_rate, 0.0002)
            self.assertEqual(tier.aum_fee_rate, 0.02)

        for aum_level in (10000.01, 200000., 300000.):
            tier = FeeTier.get_tier_for_aum_level(aum_level=aum_level, company=self.company1)
            self.assertEqual(tier.new_cash_fee_rate, 0.0003)
            self.assertEqual(tier.aum_fee_rate, 0.03)


if __name__ == '__main__':
    unittest.main()
