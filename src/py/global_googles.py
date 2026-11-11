"""
=========================================================
      The global functions of Google
=========================================================
"""

import os.path

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

