import os.path

"""
  Read data from my tiller google sheet.
"""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import numpy as np

GOOG_CREDENTIALS    = None
GOOG_SPREADSHEETS   = None
GOOG_SHEETS_SERVICE = None

# If modifying these scopes, delete the file token.json.
GOOG_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# The ID and range of a Tiller spreadsheet.
TILLER_SPRSH_ID = "1aXzmExH2i6w6aapWDUwyWVk_mlWcY7KOO9HdsEG9lE0"
#Tiller spreadsheet Name
TILLER_SPRSH_NAME = "Transactions"

TILLER_RNG_HDR = (TILLER_SPRSH_NAME + "!A1:P1")

#TILLER_ = (TILLER_SPRSH_NAME + "!A1:P1")


"""
  Initialize the google credentials for the tiller data reader.
"""
def init_credentials():
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  global GOOG_CREDENTIALS
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

  print("Initialized google credentials for tiller data reader.")

"""
  Read the header of the tiller spreadsheet and return a list of column names.
"""
def read_sprsht_header():
  print("Getting the header of the tiller spreadsheet...")

  if(GOOG_SPREADSHEETS is None):
    print("GOOG_SPREADSHEETS is None. Not Initialized..")
    return None
  try:

     hdr_range = (
        GOOG_SPREADSHEETS.values()
        .get(spreadsheetId=TILLER_SPRSH_ID, range=TILLER_RNG_HDR)
        .execute()
    )

     hdr_row = hdr_range.get("values", [])
     _,num_cols = np.array(hdr_row).shape

     print(f"Num of columns of the tiller spreadsheet : {num_cols}")
     for row in hdr_row:
      for hdr in row:
        print(f"Header {hdr}") 

     return hdr_range.get("values", [])

  except HttpError as err:
    print(err)

"""
   Main function  
"""
def main():

  global GOOG_SHEETS_SERVICE
  global GOOG_SPREADSHEETS

  init_credentials()

  if(GOOG_CREDENTIALS is None):
    print("GOOG_CREDENTIALS is None. Not Initialized..")
    exit()

  try:

    GOOG_SHEETS_SERVICE = build("sheets", "v4", credentials=GOOG_CREDENTIALS)

    # Call the Sheets API
    GOOG_SPREADSHEETS = GOOG_SHEETS_SERVICE.spreadsheets()

    hdr_row = read_sprsht_header()
    if(1): exit()
  


  except HttpError as err:
    print(err)


if __name__ == "__main__":
  main()