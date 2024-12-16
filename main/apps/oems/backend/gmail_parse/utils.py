# [START gmail_quickstart]
from __future__ import print_function
import pickle
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from pyutils.file_utils import Expand
from pyawsutils.s3      import get_obj_s3, upload_obj_s3, test_s3

# ============================================================================

PATH = Expand(__file__)

def get_credentials(scopes, key, use_s3=True, bucket='catalan-master-configs', key_base='master/gmail/'):

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.

    key        = f'{key_base}/{key}'
    token_file = os.path.join( PATH, f'cfgs/{key}' )

    if use_s3 and bucket and key and test_s3(bucket, key):
        creds = get_obj_s3( bucket, key )
    elif os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join( PATH, 'cfgs/credentials.json'), scopes)
                creds = flow.run_local_server(port=0)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join( PATH, 'cfgs/credentials.json'), scopes)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        if use_s3 and bucket and key:
            upload_obj_s3( creds, bucket, key )
        else:
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)

    return creds

# =============================================================================
