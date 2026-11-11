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

#Google API imports
import global_googles as gg
from googleapiclient.errors import HttpError

#SQLAlchemy imports
import sqlalchemy as SQA
from sqlalchemy import insert as sqa_insert
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import urllib.parse

#PostgreSQL database connection constants
PG_DRIVER = "postgresql+psycopg"
PG_USER   = "legba"
PG_PASS   = "Ediki@k0ng"
PG_HOST   = "localhost"
PG_PORT   = "5432"

SQA_URL = URL.create(
    drivername=PG_DRIVER,
    username=PG_USER,
    password=PG_PASS,
    host=PG_HOST,
    port=PG_PORT,
    database="cscfindb"
)

#Tiller spreadsheet data reader constants
#The ID of CSC.Tiller.Citibank spreadsheet.
TILLER_SPRSH_ID_BANKS    = "1qQKOMJGwyh2Eh9PTCp5UGFWvWpBasuB5xSkndKIKgRU"
TILLER_SPRSH_ID_CCARDS   = "1GlNEhYv0Mvxd3MaVNn70DbA99pYJTkSWMOPNskZmKFc"
TILLER_SPRSH_ID_CITIBANK = "1aXzmExH2i6w6aapWDUwyWVk_mlWcY7KOO9HdsEG9lE0"

TILLER_SPRSH_IDXS = {
  "BANKS":    TILLER_SPRSH_ID_BANKS,
  "CCARDS":   TILLER_SPRSH_ID_CCARDS,
  "CITIBANK": TILLER_SPRSH_ID_CITIBANK
}

#Tiller Transactions Sheet specs
TILLER_TRSC_NAME     = "Transactions"
TILLER_TRSC_RNG_DATA = (TILLER_TRSC_NAME + "!B2:P500")
TILLER_TRSC_RNG_HDR  = (TILLER_TRSC_NAME + "!B1:P1")
TILLER_TRSC_HDR_IDXS =  {
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

# =========================================================

"""
 --------------------------------------------------------------------
  Read the header of the tiller transactions spreadsheet 
  and return a list of column names.
 --------------------------------------------------------------------
"""
def read_transactions_header():
  print("Getting the header of the transactions spreadsheet...")

  if(gg.GOOG_SPREADSHEETS is None):
    print("GOOG_SPREADSHEETS is None. Not Initialized..")
    return None
  try:

     hdr_range = (
        gg.GOOG_SPREADSHEETS.values()
        .get(spreadsheetId=TILLER_SPRSH_ID_CITIBANK, range=TILLER_TRSC_RNG_HDR)
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
 ------------------------------------------------------------------------
  Build the vendors list from the transactions spreadsheet
 ------------------------------------------------------------------------
"""
def build_vendors_list(use_spreadsheet_id=TILLER_SPRSH_ID_CITIBANK):
  print("Building the vendors list from the transactions spreadsheet...")

  if(gg.GOOG_SPREADSHEETS is None):
    print("Error: GOOG_SPREADSHEETS is None. Not Initialized..")
    return

  #Create a database engine using SQLAlchemy
  print(f"  Creating database engine {SQA_URL}...")
  sqa_engine = create_engine(SQA_URL)
  print(f"  Created database engine.\n")

  vendors_table = SQA.Table("vendors", SQA.MetaData(),autoload_with=sqa_engine)
  venaddr_table = SQA.Table("vendor_addresses", SQA.MetaData(),autoload_with=sqa_engine)

  vendors_columns = vendors_table.columns.keys()
  venaddr_columns = venaddr_table.columns.keys()
  with sqa_engine.connect() as sqa_conn:
    sqa_result = sqa_conn.execute(SQA.select(vendors_table)).fetchall()
     
  print(f"Vendors columns: {vendors_columns}")
  print(f"Vendor Addresses columns: {venaddr_columns}")
 # """

  #Build a set of already existing vendors
  existing_vendors = set()
  if(len(sqa_result) > 0):
    existing_vendors.update([sqa_row[0] for sqa_row in sqa_result])

  print(f"Existing Vendors: {len(existing_vendors)}")
  #if(1): sys.exit()
  try:

     data_range = (
        gg.GOOG_SPREADSHEETS.values()
        .get(spreadsheetId=use_spreadsheet_id, range=TILLER_TRSC_RNG_DATA)
        .execute()
    )

     data_rows = data_range.get("values", [])
     num_rows,num_cols = np.array(data_rows).shape

     print(f"dimensions of transactions data: {num_rows} {num_cols}")
     print(f"Num of relevent columns of the tiller spreadsheet : {num_cols}")

     shrt_desc_idx = TILLER_TRSC_HDR_IDXS["Description"]
     full_desc_idx = TILLER_TRSC_HDR_IDXS["Full Description"]
     print(f"shrt_desc_idx  : {shrt_desc_idx} full_desc_idx {full_desc_idx}\n")

     vendors_many_list = []
     venaddr_many_list = []
       
     for row in data_rows:
      shrt_desc = row[shrt_desc_idx]
      full_desc = row[full_desc_idx]
      fast_hash = zlib.crc32((shrt_desc + full_desc).encode("utf-8"))
      #print(f"hash : {fast_hash}\t{shrt_desc}\t{full_desc}")
      if(fast_hash not in existing_vendors):
        existing_vendors.add(fast_hash)
        print(f"+++ {shrt_desc} {full_desc}")

        vendaddr_row = {}
        for col in venaddr_columns:
          if(col == "id"):
            vendaddr_row[col] = fast_hash
          else: 
            vendaddr_row[col] = ""
       
        venaddr_many_list.append(vendaddr_row)

        vendors_row   = {}
        for col in vendors_columns:
          if(col == "id"):
            vendors_row[col] = fast_hash
          elif(col == "full_desc"):
            vendors_row[col] = full_desc
          elif(col == "shrt_desc"):
            vendors_row[col] = shrt_desc
          elif(col == "type"):
            vendors_row[col] = "GENERAL"
          elif(col == "addr_id"):
            vendors_row[col] = fast_hash
          else:
            vendors_row[col] = ""
            
        vendors_many_list.append(vendors_row)
        
      else:
          print(f"=== {shrt_desc} {full_desc}")

     if(len(vendors_many_list ) > 0) :
      vendors_insert = SQA.insert(vendors_table)
      venaddr_insert = SQA.insert(venaddr_table)
      with sqa_engine.connect() as sqa_conn:
        sqa_conn.execute(venaddr_insert, venaddr_many_list) 
        sqa_conn.execute(vendors_insert, vendors_many_list)
      print(f"\nInserted {len(venaddr_many_list)} new vendor addresses into the database.\n")
     else:
      print(f"\nNo new vendors nothing to insert addresses into the database.\n")


     #print(f"Querying the vendors table...")
     #with sqa_engine.connect() as sqa_conn:
     # result = sqa_conn.execute(SQA.select(vendors_table)).fetchall()
     # print(f"Queried {len(result)} rows from the vendors table.")
     # for row in result:
     #   print(row)

  except HttpError as err:
    print(err)

  print(f"Found {len(existing_vendors)} unique vendors in the transactions spreadsheet.")
  print("Done building the vendors list from the transactions spreadsheet.")

def query_vendors_contents():
  print("Begin querying the vendors vendors table...")

  print(f"  Creating database engine {SQA_URL}...")
  sqa_engine = create_engine(SQA_URL)
  print(f"  Created database engine.\n")

  vendors_table = SQA.Table("vendors", SQA.MetaData(),autoload_with=sqa_engine)
  #venaddr_table = SQA.Table("vendor_addresses", SQA.MetaData(),autoload_with=sqa_engine)
  vendors_columns = vendors_table.columns.keys()
  #venaddr_columns = venaddr_table.columns.keys()

  print(f"Vendors columns: {vendors_columns}")
 # print(f"Vendor Addresses columns: {venaddr_columns}")

  with sqa_engine.connect() as sqa_conn:
    #Query the vendors table
    print(f"Querying the vendors table...")
    sqa_result = sqa_conn.execute(SQA.select(vendors_table)).fetchall()
    print(f"Queried {len(sqa_result)} rows from the vendors table.")
    #for sqa_row in sqa_result:
    #  print(sqa_row)

    table_ids = [sqa_row[0] for sqa_row in sqa_result]

    print(f"{len(table_ids)} rows from the vendors table.")
    print(f"Table ids {table_ids}")


  print("End   querying the vendors vendors table.")

"""
------------------------------------------------------------------------------
   Read and execute the sql script file on the database.
------------------------------------------------------------------------------
"""
def execute_sql_script(sql_fname):
  print(f"Executing sql script {sql_fname} on the database....\n")

  #Create a database engine using SQLAlchemy
  print(f"Creating database engine {SQA_URL}...")
  sqa_engine = create_engine(SQA_URL)
  print(f"Created database engine.\n\n")

  #open the SQL script file and readand execute its contents  
  with open(sql_fname, "r", encoding="utf-8") as sql_file:
    sql_script = sql_file.read()
    sql_statments = sql_script.split(";")
  with sqa_engine.connect() as sqa_conn:
    print(f"Executing sql statments on engine.\n")
    for sql_stmt in sql_statments:
      sql_stmt = sql_stmt.strip()
      #if(len(sql_stmt) > 0) and (not sql_stmt.startswith("--")):
      if(len(sql_stmt) > 0): #and (not sql_stmt.startswith("--")):
        print(f"Executing sql statement: {sql_stmt}\n")
        # Execute the SQL statement on the database
        sqa_conn.execute(text(sql_stmt))
        sqa_conn.commit()  # Commit the changes if it's a modifying statement
        print(f"\nStatement executed successfully.\n")

  print(f"\nExecuted sql script.")

"""
  -------------------------------------------------------------------------
   Create command line options 
  -------------------------------------------------------------------------
"""
def create_cmd_line_opts():
    usage = "usage: %prog spreadsheet[BANKS|CCARD|CITIBANK] [options]"
    p = optparse.OptionParser(usage=usage)
    p.add_option("--run_sql",
                 dest="run_sql_fname",
                 action="store",
                 help="Execute the sql script file on the database."
                )
    p.add_option("--out_file",
                 dest="output_fname",
                 action="store",
                 help="The output file for the results."
                )
    p.add_option("-b","--build_vendors",
                 dest="bvendors",
                 action="store_true",
                 default=False,
                 help="Build the vendors list from the given spreadsheet."
                )
    p.add_option("-q","--query_vendors",
                 dest="qvendors",
                 action="store_true",
                 default=False,
                 help="Query the vendors table contents."
                )
    return p

"""
  -------------------------------------------------------------------------
   Main function  
  -------------------------------------------------------------------------
"""
if __name__ == "__main__":

    cmd_opts  = create_cmd_line_opts()
    opts,args = cmd_opts.parse_args()

    if(len(args) < 1):
      print("Error must specify spreadsheet name. Type -h for usage")
      sys.exit(1)
    else:
      spsht_name = args[0].upper()
      if(spsht_name not in TILLER_SPRSH_IDXS):
        print(f"Error invalid spreadsheet name {spsht_name}. Type -h for usage")
        sys.exit(1)
      else:
        print(f"Spreadsheet name : {spsht_name}")

    if(None == opts.run_sql_fname) and \
      (False == opts.bvendors)     and \
      (False == opts.qvendors):
      print("Error must specify action. Type -h for usage")
      sys.exit(1)

    gg.init_googles()

    if(opts.bvendors):
        build_vendors_list(TILLER_SPRSH_IDXS[spsht_name])

    if(opts.qvendors):
        query_vendors_contents()

    elif(opts.run_sql_fname):
        execute_sql_script(opts.run_sql_fname)