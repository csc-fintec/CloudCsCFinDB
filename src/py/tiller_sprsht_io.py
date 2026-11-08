
"""
=========================================================
      Read data from my tiller google sheet.
=========================================================
"""

import os.path
import numpy as np
import zlib

import io 
import sys
import string


import shutil
import hashlib
import optparse

from googleapiclient.errors import HttpError

""""
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# If modifying these scopes, delete the file token.json.
GOOG_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

GOOG_CREDENTIALS    = None
GOOG_SPREADSHEETS   = None
GOOG_SHEETS_SERVICE = None
"""

import global_googles as gg

#The ID CSC.Tiller.Citibank spreadsheet.
TILLER_SPRSH_ID = "1aXzmExH2i6w6aapWDUwyWVk_mlWcY7KOO9HdsEG9lE0"

#Tiller Transactions Sheet specs
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
  Read the header of the tiller transactions spreadsheet 
  and return a list of column names.
 ------------------------------------------------------------------------------
"""
def read_transactions_header():
  print("Getting the header of the transactions spreadsheet...")

  if(gg.GOOG_SPREADSHEETS is None):
    print("GOOG_SPREADSHEETS is None. Not Initialized..")
    return None
  try:

     hdr_range = (
        gg.GOOG_SPREADSHEETS.values()
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

  if(gg.GOOG_SPREADSHEETS is None):
    print("GOOG_SPREADSHEETS is None. Not Initialized..")
    return

  try:

     found_vendors = set()

     data_range = (
        gg.GOOG_SPREADSHEETS.values()
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
 ------------------------------------------------------------------------------
   Read and execute the sql script file on the database.
 ------------------------------------------------------------------------------
"""

def execute_sql_script(sql_fname):
  print(f"Executing sql script {sql_fname} on the database")

  with open(sql_fname, "r", encoding="utf-8") as sql_file:
    sql_script = sql_file.read()
    sql_statments = sql_script.split(";")
    for sql_stmt in sql_statments:
      sql_stmt = sql_stmt.strip()
      if(len(sql_stmt) > 0):
        print(f"Executing sql statement: {sql_stmt}")
        # Execute the SQL statement on the database
        # (Assuming you have a database connection established)
        # db_connection.execute(sql_stmt)

"""
  -------------------------------------------------------------------------
   Create command line options 
  -------------------------------------------------------------------------
"""
def create_cmd_line_opts():
    p = optparse.OptionParser()
    p.add_option("-s","--fsql",
                 dest="sql_fname",
                 action="store",
                 help="Execute the sql script file on the database."
                )
    p.add_option("--bvendors",
                 dest="bvendors",
                 action="store_true",
                 default=False,
                 help="Build the vendors list from the tiller transactions spreadsheet."
                )

    #p.add_option("--inp",action="store",dest="inpdir")
    #p.add_option("-d",   action="store",dest="dbfile")
    #p.add_option("--dbf",action="store",dest="dbfile")
    return p

"""
  -------------------------------------------------------------------------
   Main function  
  -------------------------------------------------------------------------
"""
if __name__ == "__main__":

    cmd_opts  = create_cmd_line_opts()
    opts,args = cmd_opts.parse_args()

    if(None == opts.sql_fname) and (False == opts.bvendors):
      print("Error must specify action. Type -h for usage")
      sys.exit(1)

    gg.init_googles()

    if(opts.bvendors):
        build_vendors_list()

    elif(opts.sql_fname):
        execute_sql_script(opts.sql_fname)