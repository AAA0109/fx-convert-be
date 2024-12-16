import unittest

from django.conf import settings
from hdlib.DateTime.Date import Date

from main.apps.core.tests.base import BaseTestCase
from main.apps.ibkr.services.fb.connector import IBFBConnector
from main.apps.ibkr.services.fb.fb import IBFBService


class IBFBTestCase(BaseTestCase):

    def setUp(self) -> None:
        self.ib_fb_service = IBFBService()
        self.ib_fb_connector = IBFBConnector()

    @unittest.skipIf(not settings.IB_RUN_TESTS, "Only run if IB_RUN_TESTS is set to True")
    def test_get_uploaded_ids(self):
        today = Date.today()
        days_back = 27
        date = today - days_back
        ids = self.ib_fb_service.get_updated_upload_ids(date)
        self.assertIsInstance(ids, list)
        if len(ids) > 0:
            self.assertTrue(all(isinstance(x, int) for x in ids))
