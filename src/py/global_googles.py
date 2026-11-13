"""
=========================================================
      The global functions of Google
=========================================================
"""
import sys
import os.path

from dotenv import load_dotenv

import asyncio
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import googlemaps
from googlemaps import places

#define a quick grammer for parsing addresses...
import pyparsing as pp

adg_st_wd = pp.Word(pp.alphas + "-'")
adg_st_nm = pp.Combine(pp.OneOrMore(adg_st_wd),join_string=" ",adjacent=False)
adg_st_no = pp.Word(pp.nums + pp.alphas,min=1)
adg_street = pp.Combine(adg_st_no + pp.OneOrMore(pp.White(" ") + adg_st_nm))("street")

adg_us_state = pp.oneOf(\
  "AL AK AZ AR CA CO CT DE FL GA\
   HI ID IL IN IA KS KY LA ME MD\
   MA MI MN MS MO MT NE NV NH NJ\
   NM NY NC ND OH OK OR PA RI SC\
   SD TN TX UT VT VA WA WV WI WY"
)("state")

adg_city = pp.Word(pp.alphas + " ")("city")
adg_zip  = pp.Word(pp.nums,exact=5).addParseAction(lambda t: int(t[0]))("zipcode")
adg_ctry = pp.Word(pp.alphas)("country")
adg      = adg_street   + pp.Literal(",").suppress() + \
           adg_city     + pp.Literal(",").suppress() + \
           adg_us_state + adg_zip       + \
           pp.Optional(pp.Literal(",").suppress() + adg_ctry)

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
    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress"
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
  else:    
      raise ValueError("Missing .env for google maps api file");


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
def goog_get_business_address(bus_query : str = "Googleplex Mountain View"):
  print(f"Getting business address of {bus_query}")

  bus_name_req = {
      "textQuery": bus_query
  }

  bus_query_res = requests.post(GOOG_MAPS_URL, 
                               json=bus_name_req, 
                               headers=GOOG_MAPS_HDR)

  print(f"Got response code {bus_query_res.status_code}")
  
  if(200 == bus_query_res.status_code):
      bus_query_data = bus_query_res.json()
      bus_places = bus_query_data.get("places",[])
      print(f"Found {len(bus_places)} addresses for bus_name {bus_query}")
      if(1 == len(bus_places)):
       bus_place = bus_places[0]
       bus_name  = bus_place.get("displayName")
       bus_addr  = bus_place.get("formattedAddress")
       print(f"Name : {bus_name}")
       print(f"Addr : {bus_addr}")

       adg_parsed  = adg.parse_string(bus_addr)
       print(adg_parsed.dump())
  else:
      #print(f"NOT something for bus_name {bus_name_res.text}")
      print(f"Found NO addresses for bus_query {bus_query}")

  if(1): sys.exit(0)
