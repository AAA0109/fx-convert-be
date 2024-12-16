
from googleapiclient.discovery import build
from pygmail.utils import get_credentials

from pyutils.type_utils import infer_type, date_safe_infer_type
from pyutils.tsreader   import list2ts
from itertools import zip_longest
# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# ===============================================================

def read_sheet( spreadsheet_id, cell_rng, cred_nm='hunter-sheets.obj', header=True, imply_types=True, force=False, return_ts=False ):

    creds = get_credentials(SCOPES, cred_nm, use_s3=True)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet  = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=cell_rng).execute()
    values = result.get('values', [])

    if not values:
        ret = values
    else:
        if header:
            headers = values.pop(0)
            ret     = []
            for row in values:
                if not row[0] and not ''.join(row): continue
                if force:
                    if imply_types:
                        tmp = dict(zip_longest(headers,map(date_safe_infer_type, row)))
                    else:
                        tmp = dict(zip_longest(headers,row))
                else:
                    if imply_types:
                        tmp = dict(zip(headers,map(date_safe_infer_type, row)))
                    else:
                        tmp = dict(zip(headers,row))
                ret.append(tmp)
        else:
            ret = [ row for row in values if row[0] or ''.join(row) ]

    if return_ts:
        ret = list2ts( ret )

    return ret

# ==============================================================

if __name__ == "__main__":

    sid = '1E9EK_fkZ3Z7kL-74Gb4HGt0a0IFRgOs2Ov3OuceN3A4'
    cr  = 'Benchmarks!A1:E1000'

    x = read_sheet( sid, cr, return_ts=True )

