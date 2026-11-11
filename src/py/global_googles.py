"""
=========================================================
      The global functions of Google
=========================================================
"""

import os.path

from dotenv import load_dotenv
import googlemaps

import asyncio
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googlemaps import places


# If modifying these scopes, delete the file token.json.
GOOG_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

GOOG_CREDENTIALS    = None
GOOG_SPREADSHEETS   = None
GOOG_SHEETS_SERVICE = None

GOOG_MAPS_API       = None
GOOG_MAPS_URL       = "https://places.googleapis.com/v1/places:searchText"
GOOG_MAPS_HDR       = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": "",
    # Specify only the fields you need to control billing costs
    "X-Goog-FieldMask": "places.displayName,places.formattedAddress"
}

"""
------------------------------------------------------------------------------
  Initialize the google credentials and objects for the tiller data reader.
------------------------------------------------------------------------------
"""
def goog_init():
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  global GOOG_CREDENTIALS
  global GOOG_SPREADSHEETS
  global GOOG_SHEETS_SERVICE

  global GOOG_MAPS_API
  global GOOG_MAPS_HDR

  print("Initializing googlemaps..")
  if os.path.exists("./.env"):
    load_dotenv()
    gmaps_api_key = os.getenv("GOOG_MAPS_API_KEY")
    if not gmaps_api_key:
      raise ValueError("API KEY GOOG_MAPS_API_KEY not found. Check .env file")
    else:
      GOOG_MAPS_API = googlemaps.Client(key=gmaps_api_key)
      GOOG_MAPS_HDR["X-Goog-Api-Key"] = gmaps_api_key
      print("Initialized google maps api.")


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
  Initialize the google credentials and objects for the tiller data reader.
------------------------------------------------------------------------------
"""
async def goog_get_business_address(bus_name: str):
    print(f"Getting business address from {bus_name}.\n")

    client = places.PlacesAsyncClient(
        client_options={"api_key": GOOG_MAPS_API}
    )

    request = places.SearchTextRequest(text_query=bus_name)

    # Prefix fields with 'places.' for Text Search
    field_mask = (
        "places.id,places.displayName,places.formattedAddress,"
        "places.addressComponents"
    )

    response = await client.search_text(
        request=request, metadata=[("x-goog-fieldmask", field_mask)]
    )

    for place in response.places:
        print(f"Name: {place.display_name.text}")
        print(f"Address: {place.formatted_address}")
        print(f"Place ID: {place.id}\n")

