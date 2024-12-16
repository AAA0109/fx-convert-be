import base64
import email
import logging
import mimetypes
from email.message import EmailMessage
from typing import Optional, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from main.apps.core.models import VendorOauth


class GmailService:
    """
    A service class for interacting with Gmail via dynamically retrieved user credentials
    from a database. It facilitates operations such as sending emails, fetching emails, and
    parsing email content, using the OAuth2 credentials associated with a specific user.

    This class is intended for use in environments where Gmail access tokens and refresh tokens
    are stored and managed per-user basis, allowing personalized interaction with the Gmail API.

    Attributes:
        as_email (str): The email address of the user for whom the service is impersonated.
        service (googleapiclient.discovery.Resource): An instance of the Gmail API service object,
        initialized with user-specific credentials.
    """

    def __init__(self, oauth: VendorOauth):
        """
        Initializes the Gmail service for a specific user by retrieving their stored OAuth2
        credentials from the database and using them to authenticate API requests.

        The method expects the user model instance that corresponds to the user whose Gmail
        service is being accessed. It attempts to fetch the user's stored credentials and use them
        to build the Gmail service.

        Args:
            user (settings.AUTH_USER_MODEL): The Django user model instance for whom the Gmail
            service is being set up. This user's email address is used to identify the Gmail account.
        """
        self.as_email = oauth.user.email
        logging.info(f"[GmailService] Setting up Gmail service for {self.as_email}")

        # Recreate the Credentials object
        credentials = Credentials(
            token=oauth.access_token,
            refresh_token=oauth.refresh_token,
            token_uri=oauth.token_uri,
            client_id=oauth.client_id,
            client_secret=oauth.client_secret,
            scopes=oauth.scopes
        )

        # Build the Gmail service
        self.service = build('gmail', 'v1', credentials=credentials)
        logging.info(f"[GmailService] Completed setting up Gmail service for {self.as_email}")

    def fetch_and_parse_email(self, message_id: str) -> Optional[EmailMessage]:
        """
        Fetches an email by its ID and returns it as an EmailMessage object.

        Args:
            message_id (str): The ID of the email to fetch.

        Returns:
            EmailMessage | None: The fetched email as a Message object, or None if an error occurred.
        """
        try:
            email_data = self.service.users().messages().get(userId="me", id=message_id, format='raw').execute()
            msg_str = base64.urlsafe_b64decode(email_data['raw'].encode('ASCII'))
            mime_msg = email.message_from_bytes(msg_str, policy=email.policy.default)

            return mime_msg
        except Exception as error:
            logging.error(f"[GmailService] Error fetching email for {self.as_email} with ID {message_id}: {error}",
                          exc_info=True)
            return None

    def read_emails(self, max_results: int = 500) -> List[EmailMessage]:
        """
        Reads the latest emails up to a specified number and returns them as a list of Message objects.

        Args:
            max_results (int): The maximum number of emails to read.

        Returns:
            list[EmailMessage]: A list of the latest Message objects.
        """
        try:
            logging.info(f"[GmailService] Reading messages for {self.as_email}")
            response = self.service.users().messages().list(userId="me", maxResults=max_results).execute()
            message_ids = response.get("messages", [])

            messages = [
                self.fetch_and_parse_email(message_id['id'])
                for message_id in message_ids
                if message_id.get('id')
            ]

            return [message for message in messages if message is not None]  # Filter out any failures
        except Exception as error:
            logging.error(f"[GmailService] Error reading messages for {self.as_email}: {error}", exc_info=True)
            return []

    def send_email(
        self,
        to_email: str,
        email_subject: str,
        email_content: str,
        email_attachment_path: Optional[str] = None,
        email_attachment_filename: str = "file_attachment",
    ) -> Optional[dict]:
        """
        Sends an email with optional attachment.

        Args:
            to_email (str): The recipient's email address.
            email_subject (str): The subject of the email.
            email_content (str): The text content of the email.
            email_attachment_path (Optional[str]): Path to the file to attach, if any.
            email_attachment_filename (str): Filename to use for the attachment. Defaults to "file_attachment".

        Returns:
            dict | None: The response from the Gmail API if the email is successfully sent, otherwise None.
        """
        logging.info(f"[GmailService] Sending email from {self.as_email} to {to_email}")
        try:
            message = EmailMessage()
            message["From"] = self.as_email
            message["To"] = to_email
            message["Subject"] = email_subject
            message.set_content(email_content)

            if email_attachment_path:
                type_subtype, _ = mimetypes.guess_type(email_attachment_path)
                if type_subtype is None:
                    maintype, subtype = 'application', 'octet-stream'
                else:
                    maintype, subtype = type_subtype.split('/')

                with open(email_attachment_path, "rb") as fp:
                    attachment_data = fp.read()
                message.add_attachment(attachment_data, maintype, subtype, filename=email_attachment_filename)

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}
            send_message = self.service.users().messages().send(userId="me", body=create_message).execute()

            logging.info(
                f"[GmailService] Sent email from {self.as_email} to {to_email} (message_id={send_message['id']})")
            return send_message
        except Exception as error:
            logging.error(f"[GmailService] Error sending email from {self.as_email} to {to_email}", exc_info=True)
            return None
