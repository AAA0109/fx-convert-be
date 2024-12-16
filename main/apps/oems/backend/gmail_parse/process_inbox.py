# [START gmail_quickstart]
from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import libpydatetime
import base64

from pyutils.date_utils import epoch_time_to_dt
from pyutils.file_utils import Expand
from pyawsutils.s3      import get_obj_s3, upload_obj_s3, test_s3

# =============================================================================

PATH = Expand(__file__)

class ProcessInbox:

    # If modifying these scopes, delete the file token.pickle.
    SCOPES  = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.modify']
    SERVICE = None
    CREDS   = None

    def __init__( self, auth_s3=True, auth_bucket='catalan-master-configs', auth_key='master/gmail/hunter-new-auth-token.obj', fetch_kwargs={} ):

        self.auth_s3      = auth_s3
        self.auth_bucket  = auth_bucket
        self.auth_key     = auth_key
        self.fetch_kwargs = fetch_kwargs

    # ==========================================================================

    def get_credentials(self, token_file='cfgs/new-token.pickle', cred_file='cfgs/credentials.json'):

        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.

        token_file = os.path.join( PATH, token_file )

        if self.auth_s3 and self.auth_bucket and self.auth_key and test_s3(self.auth_bucket, self.auth_key):
            creds = get_obj_s3( self.auth_bucket, self.auth_key )
        elif os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.path.join( PATH, cred_file), self.SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            if self.auth_bucket and self.auth_key:
                upload_obj_s3( creds, self.auth_bucket, self.auth_key )
            else:
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)

        return creds

    # ============================================================================

    @staticmethod
    def decode_msg( data ):
        return base64.urlsafe_b64decode(data).decode()

    @staticmethod
    def get_msg_date( msg ):
        return epoch_time_to_dt( int(msg['internalDate']) )

    # ============================================================================

    def logon( self ):
        ProcessInbox.CREDS   = self.get_credentials()
        ProcessInbox.SERVICE = build('gmail', 'v1', credentials = self.CREDS)

    def fetch_messages( self, **kwargs):
        return self.SERVICE.users().messages().list(userId='me', **kwargs).execute()

    def fetch_message(self, message_id):
        try:
            return self.SERVICE.users().messages().get(userId='me', id=message_id).execute()
        except:
            return None

    def fetch_attachment(self, message, att_id):
        # Fetch the attachment
        att = self.SERVICE.users().messages().attachments().get(userId='me', messageId=message['id'], id=att_id).execute()
        return base64.urlsafe_b64decode(att['data'].encode('UTF-8'))

    def fetch_attachments( self, message ):
        ret = []
        for part in message['payload']['parts']:
            # Check if there is an attachment to the email
            if part['filename']:
                # Checks if the file is part of the email itself (such as an image)
                if 'data' in part['body']:
                    continue
                    raise NotImplementedError
                    data = part['body']['data']
                else:
                    # If the file is not a part of the email itself, it is probably an attachment
                    file_data = self.fetch_attachment(message, part['body']['attachmentId'])
                    ret.append({'name': part['filename'], 'data': file_data })
        return ret

    def fetch_email_body( self, message ):
        ret = []
        for part in message['payload']['parts']:
            if not part['filename'] and 'data' in part['body']:
                ret.append( self.decode_msg( part['body']['data'] ) )
        return ret

    def fetch_email_info( self, message ):

        ret = dict.fromkeys(['Delivered-To','Return-Path','Date','From','To','Cc','Subject'])

        for header in message['payload']['headers']:
            if header['name'] in ret:
                ret[ header['name'] ] = header['value']

        return ret

    def mark_unread( self, message_id ):
        self.SERVICE.users().messages().modify(userId='me', id=message_id, body={'removeLabelIds': ['UNREAD']}).execute()

    def get_messages( self, **kwargs ):
        try:
            results = self.fetch_messages( **kwargs )
        except BrokenPipeError:
            self.logon()
            results = self.fetch_messages( **kwargs )

        return results.get('messages', [])

    # =========================================================================

    def user_start( self ):
        # any state setup prior to processing message
        pass

    def user_parse( self, message_id, msg ):
        # parse the message
        pass

    def user_end( self ):
        # any state cleanup after processing
        pass

    # =========================================================================

    def run( self  ):

        self.user_start()

        if self.SERVICE is None:
            self.logon()

        messages = self.get_messages( **self.fetch_kwargs )
        for message in messages:
            msg = self.fetch_message( message['id'] )
            if msg:
                self.user_parse( message['id'], msg )

        self.user_end()

    # =========================================================================


