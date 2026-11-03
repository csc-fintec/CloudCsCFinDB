import os.path
import numpy as np
import zlib

"""
  Read data from my tiller google sheet.
"""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the file token.json.
GOOG_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

GOOG_CREDENTIALS    = None
GOOG_SPREADSHEETS   = None
GOOG_SHEETS_SERVICE = None

#The ID and range of a Tiller spreadsheet.
TILLER_SPRSH_ID = "1aXzmExH2i6w6aapWDUwyWVk_mlWcY7KOO9HdsEG9lE0"

#Tiller Transactions Sheet
TILLER_TRSC_NAME     = "Transactions"
TILLER_TRSC_RNG_DATA = (TILLER_TRSC_NAME + "!B2:P500")
TILLER_TRSC_RNG_HDR  = (TILLER_TRSC_NAME + "!B1:P1")
TILLER_TRSC_HDR_IDX = {
	 "Date": 0,
	 "Description": 1,
	 "Category": 2,
	 "Amount": 3, 
	 "Account": 4,
	 "Account #": 5,
	 "Institution": 6,
	 "Month": 7,
	 "Week": 8,
	 "Transaction ID": 9,
	 "Account ID": 10,
	 "Check Number": 11,
	 "Full Description": 12,
	 "Date Added": 13,
	 "Category Hint": 14
}

"""
------------------------------------------------------------------------------
  Initialize the google credentials and objects for the tiller data reader.
------------------------------------------------------------------------------
"""
def init_googles():
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  global GOOG_CREDENTIALS
  global GOOG_SPREADSHEETS
  global GOOG_SHEETS_SERVICE

  print("Initializing google credentials for tiller data reader...")

  if os.path.exists("./token.json"):
    GOOG_CREDENTIALS = Credentials.from_authorized_user_file("token.json", GOOG_SCOPES)

  # If there are no (valid) credentials available, let the user log in.
  if not GOOG_CREDENTIALS or not GOOG_CREDENTIALS.valid:
    if GOOG_CREDENTIALS and GOOG_CREDENTIALS.expired and GOOG_CREDENTIALS.refresh_token:
      GOOG_CREDENTIALS.refresh(Request())
    else:
      print('No valid credentials available. Please run the function init_credentials script to authorize access.') 
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", GOOG_SCOPES
      )
      GOOG_CREDENTIALS = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(GOOG_CREDENTIALS.to_json())

  # Build the service object for the Google Sheets API
  GOOG_SHEETS_SERVICE = build("sheets", "v4", credentials=GOOG_CREDENTIALS)

  # Call the Sheets API
  GOOG_SPREADSHEETS = GOOG_SHEETS_SERVICE.spreadsheets()

  print("Initialized google credentials for tiller data reader.")

"""
 ------------------------------------------------------------------------------
  Read the header of the tiller transactions spreadsheet 
  and return a list of column names.
 ------------------------------------------------------------------------------
"""
def read_transactions_header():
  print("Getting the header of the transactions spreadsheet...")

  if(GOOG_SPREADSHEETS is None):
    print("GOOG_SPREADSHEETS is None. Not Initialized..")
    return None
  try:

     hdr_range = (
        GOOG_SPREADSHEETS.values()
        .get(spreadsheetId=TILLER_SPRSH_ID, range=TILLER_TRSC_RNG_HDR)
        .execute()
    )

     hdr_row = hdr_range.get("values", [])
     _,num_cols = np.array(hdr_row).shape
     print(f"Num of relenvant columns of the tiller spreadsheet : {num_cols}")
     col_idx = 1
     for row in hdr_row:
      for hdr in row:
        #print(f"{col_idx:02d} \"{hdr}\"") 
        print(f"\t \"{hdr}\": {col_idx:02d},")
        col_idx += 1

     return hdr_row

  except HttpError as err:
    print(err)

  return None

"""
 ------------------------------------------------------------------------------
  Build the vendors list from the transactions spreadsheet
 ------------------------------------------------------------------------------
"""
def build_vendors_list():
  print("Getting the data from the transactions spreadsheet...")

  #global TILLER_TRSC_HDR_IDX

  if(GOOG_SPREADSHEETS is None):
    print("GOOG_SPREADSHEETS is None. Not Initialized..")
    return

  try:

     found_vendors = set()

     data_range = (
        GOOG_SPREADSHEETS.values()
        .get(spreadsheetId=TILLER_SPRSH_ID, range=TILLER_TRSC_RNG_DATA)
        .execute()
    )

     data_rows = data_range.get("values", [])
     num_rows,num_cols = np.array(data_rows).shape

     print(f"dimensions of transactions data: {num_rows} {num_cols}")
     print(f"Num of relenvant columns of the tiller spreadsheet : {num_cols}")

     shrt_desc_idx = TILLER_TRSC_HDR_IDX["Description"]
     full_desc_idx = TILLER_TRSC_HDR_IDX["Full Description"]

     print(f"shrt_desc_idx : {shrt_desc_idx} full_desc_idx {full_desc_idx}")

     for row in data_rows:
      shrt_desc = row[shrt_desc_idx]
      full_desc = row[full_desc_idx]
      fast_hash = zlib.crc32((shrt_desc + full_desc).encode("utf-8"))
      #print(f"hash : {fast_hash}\t{shrt_desc}\t{full_desc}")
      if(fast_hash not in found_vendors):
        found_vendors.add(fast_hash)
        print(f"+++ {shrt_desc} {full_desc}")
      else:
          print(f"=== {shrt_desc} {full_desc}")


  except HttpError as err:
    print(err)

"""
  -------------------------------------------------------------------------
   Main function  
  -------------------------------------------------------------------------
"""
def main():

  init_googles()

  build_vendors_list()

  #hdr_row = read_transactions_header()

if __name__ == "__main__":
  main()