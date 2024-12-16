import unittest
from unittest.mock import patch

from main.apps.ibkr.services import TWSClientID


class TestTWSClientID(unittest.TestCase):

    @patch('django.core.cache.cache')
    def test_get_client_id_from_internal_service(self, mock_cache):
        # Mock the cache.get method to simulate an available client_id
        mock_cache.get.return_value = None

        # Create an instance of TWSClientID
        tws_client = TWSClientID(min_client_id=5, max_client_id=32)

        # Call the method
        client_id = tws_client.get_client_id_from_internal_service()

        # Check if the returned client_id is within the expected range
        self.assertTrue(5 <= client_id <= 32)

    @patch('django.core.cache.cache')
    def test_release_client_id_from_internal_service(self, mock_cache):
        # Mock the cache.delete method
        mock_cache.delete.return_value = None

        # Create an instance of TWSClientID
        tws_client = TWSClientID(min_client_id=5, max_client_id=32)
        tws_client.client_id = 10  # Set a mock client_id for testing

        # Call the method
        result = tws_client.release_client_id_from_internal_service()

        # Check if the result is True, indicating successful release
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
