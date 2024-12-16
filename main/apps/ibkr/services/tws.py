import logging
import time

import requests
from django.conf import settings
from django.core.cache import cache


class TWSClientID:
    client_id = None
    retries = 0

    def __init__(self, min_client_id, max_client_id):
        self.min_client_id = min_client_id if min_client_id else 5
        self.max_client_id = max_client_id if max_client_id else 32

    def get_client_id(self):
        logging.info(
            f"Getting TWS CLIENT_ID with TWS_CLIENTID_RESERVATION_API_URL={settings.TWS_CLIENTID_RESERVATION_API_URL}")

        if bool(settings.TWS_CLIENTID_RESERVATION_API_URL):
            logging.info(f"Getting TWS CLIENT_ID using external_service")
            self.client_id = self.get_client_id_from_external_service()
        else:
            logging.info(f"Getting TWS CLIENT_ID using internal_service")
            self.client_id = self.get_client_id_from_internal_service()

        if self.client_id is None:
            logging.warning("Failed to get TWS CLIENT_ID")
            raise Exception("Failed to get TWS CLIENT_ID")

        logging.info(f"TWS CLIENT_ID is {self.client_id}")
        return self.client_id

    def release_client_id(self):
        logging.info(
            f"Releasing TWS CLIENT_ID={self.client_id} with TWS_CLIENTID_RESERVATION_API_URL={settings.TWS_CLIENTID_RESERVATION_API_URL}")
        _release: bool = False

        if bool(settings.TWS_CLIENTID_RESERVATION_API_URL):
            logging.info(f"Releasing TWS CLIENT_ID using external_service ")
            _release = self.release_client_id_from_external_service()
        else:
            logging.info(f"Releasing TWS CLIENT_ID using internal_service")
            _release = self.release_client_id_from_internal_service()

        if not _release:
            logging.warning("Failed to release TWS CLIENT_ID")
            raise Exception("Failed to release TWS CLIENT_ID")
        else:
            self.client_id = None

    def get_client_id_from_external_service(self) -> int:
        while (self.retries < settings.TWS_CLIENTID_RESERVATION_MAX_RETRIES) and (not self.client_id):
            try:
                response = requests.post(f"{settings.TWS_CLIENTID_RESERVATION_API_URL}/reserve")
                response.raise_for_status()
                response_json = response.json()
                return int(response_json["slot_number"])
            except requests.exceptions.HTTPError as e:
                logging.warning(f"Error reserving client_id: {e}")
                self.retries += 1
                if self.retries < settings.TWS_CLIENTID_RESERVATION_MAX_RETRIES:
                    logging.info(
                        f"Retrying in 5 seconds (Attempt {self.retries}/{settings.TWS_CLIENTID_RESERVATION_MAX_RETRIES})")
                    time.sleep(settings.TWS_CLIENTID_RESERVATION_WAIT_BEFORE_RETRY_SECONDS)

    def get_client_id_from_internal_service(self) -> int:
        while (self.retries < settings.TWS_CLIENTID_RESERVATION_MAX_RETRIES) and (not self.client_id):
            try:
                for slot_number in range(self.min_client_id, self.max_client_id + 1):
                    if not cache.get(f"client_id_{slot_number}"):
                        cache.add(key=f"client_id_{slot_number}", value="reserved",
                                  timeout=settings.TWS_CLIENTID_RESERVATION_TIMEOUT_SECONDS)
                        return slot_number
            except requests.exceptions.HTTPError as e:
                logging.warning(f"Error reserving client_id: {e}")
                self.retries += 1
                if self.retries < settings.TWS_CLIENTID_RESERVATION_MAX_RETRIES:
                    logging.info(
                        f"Retrying in 5 seconds (Attempt {self.retries}/{settings.TWS_CLIENTID_RESERVATION_MAX_RETRIES})")
                    time.sleep(settings.TWS_CLIENTID_RESERVATION_WAIT_BEFORE_RETRY_SECONDS)

    def release_client_id_from_external_service(self):
        try:
            response = requests.post(f"{settings.TWS_CLIENTID_RESERVATION_API_URL}/release/{self.client_id}")
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            logging.warning(f"Error releasing client_id {self.client_id}: {e}")

    def release_client_id_from_internal_service(self):
        try:
            cache.delete(key=f"client_id_{self.client_id}")
            return True
        except Exception as e:
            logging.warning(f"Error releasing client_id {self.client_id}: {e}")
