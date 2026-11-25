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

from datetime import datetime
from dotenv import load_dotenv

#Google API imports
import global_googles as gg
import asyncio
from googleapiclient.errors import HttpError

#SQLAlchemy imports
import sqlalchemy as SQA
from sqlalchemy import insert as sqa_insert
from sqlalchemy import create_engine, text,inspect
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
    database="cscfindbx"
)

#Tiller spreadsheet data reader constants
#The ID of CSC.Tiller.Citibank spreadsheet.
TILLER_SPRSH_ID_BANKS    = "1qQKOMJGwyh2Eh9PTCp5UGFWvWpBasuB5xSkndKIKgRU"
TILLER_SPRSH_ID_CCARDS   = "1GlNEhYv0Mvxd3MaVNn70DbA99pYJTkSWMOPNskZmKFc"
TILLER_SPRSH_ID_CITIBANK = "1aXzmExH2i6w6aapWDUwyWVk_mlWcY7KOO9HdsEG9lE0"

TILLER_SPRSH_DICT = {
  "CITIBANK": TILLER_SPRSH_ID_CITIBANK,
  "CCARDS":   TILLER_SPRSH_ID_CCARDS,
  "BANKS":    TILLER_SPRSH_ID_BANKS
}

#Tiller Transactions Sheet specs
TILLER_TRSC_NAME     = "Transactions"
TILLER_TRSC_RNG_DATA = (TILLER_TRSC_NAME + "!B2:P3000")
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

#Database constants
DB_EMPTYADDR_HASH  =  zlib.crc32(
                   ("NO location_name"  +
                    "NO address"        +
                    "NO city"           +
                    "NO state"          +
                    "NO zipcode"        +
                    "NO country"        +
                    "NO phoneno").encode("utf-8"))

DB_EMPTYADDR_LIST = [{
      "id"            : DB_EMPTYADDR_HASH,
      "location_name" : "NO location_name",
      "address"       : "NO address",
      "city"          : "NO city",
      "state"         : "XX",
      "zipcode"       : "XXXXX",
      "country"       : "XXX",
      "phoneno"       : ""
  }]

#How many records for one add requst to the database
DB_ADD_TEMPO=50

# =========================================================

"""
 ------------------------------------------------------------------------
  Build the information in db from the transactions spreadsheet
 ------------------------------------------------------------------------
"""
def build_db_from_sprsht(spreadsheet_ky : str = "CITIBANK",
                         spreadsheet_id : str = TILLER_SPRSH_ID_CITIBANK):
  """ build the database tables from the transactions spreadsheet.

    Args:
       spreadsheet_ky: The dictionary key of the spreadsheet to query
       spreadsheet_id: The SHEETS ID of the spreadsheet to query

    Returns:
        Nothing

    Raises:
        Nothing
  """

  print("Building the database from the transactions spreadsheet...")

  if(gg.GOOG_SPREADSHEETS is None):
    print("Error: GOOG_SPREADSHEETS is None. Not Initialized..")
    return

  #Create a database engine using SQLAlchemy
  print(f"  Creating database engine {SQA_URL}...")
  sqa_engine = create_engine(SQA_URL)
  print(f"  Created database engine.\n")

  vendors_table = SQA.Table("vendors",          SQA.MetaData(),autoload_with=sqa_engine)
  venaddr_table = SQA.Table("vendor_addresses", SQA.MetaData(),autoload_with=sqa_engine)

  fininst_table = SQA.Table("financial_instruments", SQA.MetaData(),autoload_with=sqa_engine)
  finaddr_table = SQA.Table("financial_addresses",   SQA.MetaData(),autoload_with=sqa_engine)

  vendors_columns = vendors_table.columns.keys()
  #venaddr_columns = venaddr_table.columns.keys()
  #fininst_columns = fininst_table.columns.keys()
  #finaddr_columns = finaddr_table.columns.keys()

  #-------------------------------------------------------------------------------
  #Sub function to add an empty address place holder to the addresses table...
  #-------------------------------------------------------------------------------
  def add_emptyaddr_to(db_table):
    print(f"\n!!!!----------------------------------------------------------------")
    print(f"!!! Inserting empty address into into the database\n")
    empaddr_insert = SQA.insert(db_table)
    with sqa_engine.begin() as sqa_conn:
         sqa_conn.execute(empaddr_insert, DB_EMPTYADDR_LIST) 
    print(f"!!! -------------------------------------------------------------------\n")
  #-------------------------------------------------------------------------------
  #print(f"Vendors columns: {vendors_columns}")
  #print(f"Vendo sqa_stmt = SQA.select(db_table.c.id)

  vendors_id_stmt = SQA.select(vendors_table.c.id)
  venaddr_id_stmt = SQA.select(venaddr_table.c.id)
  fininst_id_stmt = SQA.select(fininst_table.c.id)
  finaddr_id_stmt = SQA.select(finaddr_table.c.id)

  #Get all the rows from the database...
  with sqa_engine.connect() as sqa_conn:
    sqa_vendors_result = sqa_conn.scalars(vendors_id_stmt).all()
    sqa_venaddr_result = sqa_conn.scalars(venaddr_id_stmt).all()
    sqa_fininst_result = sqa_conn.scalars(fininst_id_stmt).all()
    sqa_finaddr_result = sqa_conn.scalars(finaddr_id_stmt).all()

    #sqa_vendors_result = sqa_conn.execute(SQA.select(vendors_table)).fetchall()
    #sqa_venaddr_result = sqa_conn.execute(SQA.select(venaddr_table)).fetchall()
    #sqa_fininst_result = sqa_conn.execute(SQA.select(fininst_table)).fetchall()
    #sqa_finaddr_result = sqa_conn.execute(SQA.select(finaddr_table)).fetchall()
     
  #Build the set of already existing items read from database...
  existing_vendors = set()
  existing_venaddr = set()
  existing_fininst = set()
  existing_finaddr = set()

  #Load up an existing set with existing ids from the database
  if(len(sqa_vendors_result) > 0):
    existing_vendors.update(sqa_vendors_result)
    #existing_vendors.update([sqa_row[0] for sqa_row in sqa_vendors_result])
    print(f"---Begin with existing Vendors: {len(existing_vendors)}")

  if(len(sqa_venaddr_result) > 0):
    existing_venaddr.update(sqa_venaddr_result)
    #existing_venaddr.update([sqa_row[0] for sqa_row in sqa_venaddr_result])
    print(f"---Begin with existing Venaddr: {len(existing_venaddr)}")
  else:
    add_emptyaddr_to(venaddr_table)

  if(len(sqa_fininst_result) > 0):
    existing_fininst.update(sqa_fininst_result)
    #existing_fininst.update([sqa_row[0] for sqa_row in sqa_fininst_result])
    print(f"---Begin with existing Fininst: {len(existing_fininst)}")

  if(len(sqa_finaddr_result) > 0):
    existing_finaddr.update(sqa_finaddr_result)
    #existing_finaddr.update([sqa_row[0] for sqa_row in sqa_finaddr_result])
    print(f"---Begin with existing Finaddr: {len(existing_finaddr)}")
  else:
    add_emptyaddr_to(finaddr_table)


  #-------------------------------------------------------------------------------
  #Sub function to add to tables in database
  #-------------------------------------------------------------------------------
  def add_to_db(db_table,table_rows):
    print(f"\n!!!!----------------------------------------------------------------")
    print(f"!!! Inserting {len(table_rows)} new data into the database,table\n")
    table_insert = SQA.insert(db_table)
    with sqa_engine.begin() as sqa_conn:
        sqa_conn.execute(table_insert, table_rows) 
    print(f"!!! Inserted {len(table_rows)} new data into the database.")
    print(f"!!! -------------------------------------------------------------------\n")
    table_rows.clear()

  #-------------------------------------------------------------------------------
  #Sub function to add vendor tables in database
  #-------------------------------------------------------------------------------
  def add_vend_db():
    print(f"\n!!!!----------------------------------------------------------------")
    print(f"!!! Inserting {len(vendors_addrows_list)} new vendors into the database")
    print(f"!!! Inserting {len(venaddr_addrows_list)} new vendor addresses into the database\n")
    #print(f"---\n{vendors_many_list}\n---\n")
    #print(f"---\n{venaddr_many_list}\n---\n")
    vendors_insert = SQA.insert(vendors_table)
    venaddr_insert = SQA.insert(venaddr_table)
    have_venaddr  = True if len(venaddr_addrows_list) > 0 else False
    with sqa_engine.begin() as sqa_conn:
        if have_venaddr: 
          sqa_conn.execute(venaddr_insert, venaddr_addrows_list) 
        sqa_conn.execute(vendors_insert, vendors_addrows_list)
    print(f"!!! Inserted {len(vendors_addrows_list)} new vendors into the database.")
    print(f"!!! Inserted {len(venaddr_addrows_list)} new vendor addresses into the database\n")
    #print(f"!!! -------------------------------------------------------------------\n")
    vendors_addrows_list.clear()
    venaddr_addrows_list.clear()
  #-------------------------------------------------------------------------------

  #-------------------------------------------------------------------------------
  #Sub function to add financial tables to database
  #-------------------------------------------------------------------------------
  def add_fina_db():
    print(f"\n!!!!----------------------------------------------------------------")
    print(f"!!! Inserting {len(fininst_addrows_list)} new financial business  into the database.")
    print(f"!!! Inserting {len(finaddr_addrows_list)} new financial addresses into the database.")
    have_finaddr  = True if len(finaddr_addrows_list) > 0 else False
    fininst_insert = SQA.insert(fininst_table)
    finaddr_insert = SQA.insert(finaddr_table)
    with sqa_engine.begin() as sqa_conn:
        if have_finaddr: 
          sqa_conn.execute(finaddr_insert, finaddr_addrows_list)
        sqa_conn.execute(fininst_insert, fininst_addrows_list) 
    print(f"!!! Inserted {len(fininst_addrows_list)} new financial business  into the database.")
    print(f"!!! Inserted {len(finaddr_addrows_list)} new financial addresses into the database.")
    print(f"!!!!----------------------------------------------------------------\n")
    fininst_addrows_list.clear()
    finaddr_addrows_list.clear()
  #----------------------------------------------------------------------------------

  try:
     #-------------------------------------------------------------------------------
     #      Load the data from the spreadsheet here.
     #-------------------------------------------------------------------------------
     spsht_data_range = (
        gg.GOOG_SPREADSHEETS.values()
          .get(spreadsheetId=spreadsheet_id, range=TILLER_TRSC_RNG_DATA)
          .execute()
     )

     spsht_data_rows = spsht_data_range.get("values", [])
     num_rows,num_cols = np.array(spsht_data_rows).shape
     print(f"rows:{num_rows} X cols:{num_cols}. Relevant content the tiller spreadsheet.\n")

     shrt_desc_idx = TILLER_TRSC_HDR_IDXS["Description"]
     full_desc_idx = TILLER_TRSC_HDR_IDXS["Full Description"]
     acntnm_idx    = TILLER_TRSC_HDR_IDXS["Account"]
     acntno_idx    = TILLER_TRSC_HDR_IDXS["Account #"]  #Not actual account number. An abriavation e.g. X1245
     instut_idx    = TILLER_TRSC_HDR_IDXS["Institution"]

     vendors_addrows_list = []
     venaddr_addrows_list = []
     finaddr_addrows_list = []
     fininst_addrows_list = []

     vdx = 0 
     fdx = 0  

     #------------------------------------------------------------------
     # Go through all the rows of the spreadsheet, check the vendors 
     # already exist, and add them to a running tally if not,
     # stop every DB_ADD_TEMPO times to add them...
     #------------------------------------------------------------------
     for rdx,spsht_row in enumerate(spsht_data_rows):
      
      shrt_desc = spsht_row[shrt_desc_idx]
      full_desc = spsht_row[full_desc_idx]
      instut    = spsht_row[instut_idx]
      acntno    = spsht_row[acntno_idx]
      acntnm    = spsht_row[acntnm_idx]

      vend_hash = zlib.crc32((shrt_desc + full_desc).encode("utf-8"))
      fina_hash = zlib.crc32((acntno + instut + acntnm).encode("utf-8"))

      #------------------------------------------------------------------
      #  Adding to vendors
      #------------------------------------------------------------------
      if(vend_hash not in existing_vendors):
        existing_vendors.add(vend_hash)
        vdx = vdx + 1
        vaddr_hash = DB_EMPTYADDR_HASH
        print(f"+++ {rdx} from spreadsheet is {vdx} new vendor.")
        print(f"    {len(shrt_desc)} : {shrt_desc}")
        print(f"    {len(full_desc)} : {full_desc}")

        goog_businfo = gg.goog_get_business_address(shrt_desc)
        has_businfo  = True if len(goog_businfo) > 0 else False
        print(f"Got business info of {len(goog_businfo)}")

        if has_businfo:
          taddr_hash = zlib.crc32(
                      (goog_businfo.get("street")  +
                       goog_businfo.get("city")    +
                       goog_businfo.get("state")   +
                       str(goog_businfo.get("zipcode")) +
                       goog_businfo.get("country")).encode("utf-8"))

          if(taddr_hash not in existing_venaddr):
            existing_venaddr.add(taddr_hash)
            vaddr_hash = taddr_hash
            vendaddr_cols = [
              "id",
              "business_name",
              "address",
              "city",
              "state",
              "zipcode",
              "country",
              "phoneno"
            ]
            vendaddr_vals = [
              vaddr_hash,
              goog_businfo.get("busname"),
              goog_businfo.get("street"),
              goog_businfo.get("city"),
              goog_businfo.get("state"),
              goog_businfo.get("zipcode"),
              goog_businfo.get("country"),
              ""
            ]
            venaddr_addrows_list.append({k: v for k,v in zip(vendaddr_cols,vendaddr_vals)})
          #
          else: vaddr_hash = taddr_hash

        vendor_cols = [
            "id",
            "type",
            "business_name",
            "shrt_desc",
            "full_desc",
            "website",
            "addr_id"
        ]
        vendor_vals = [
            vend_hash,
            "GENERAL",
             goog_businfo.get("busname") if has_businfo else "",
             shrt_desc,
             full_desc,
             "",
             vaddr_hash
        ]
        vendors_addrows_list.append({k: v for k,v in zip(vendor_cols,vendor_vals)})

        bAddToDb = True if(0 == (len(vendors_addrows_list) % DB_ADD_TEMPO)) else False
        if (True == bAddToDb): add_vend_db()

      else:
          print(f"=== {rdx} from spreadsheet already exists.")
          print(f"    {len(shrt_desc)} : {shrt_desc}")
          print(f"    {len(full_desc)} : {full_desc}")
      
      #------------------------------------------------------------------
      #    Adding the financials information...
      #------------------------------------------------------------------
      if(fina_hash not in existing_fininst):
        existing_fininst.add(fina_hash)
        fdx = fdx + 1
        faddr_hash = DB_EMPTYADDR_HASH
        print(f"+++ {fdx} new financial to add.")
        print(f"    {len(instut)} : {instut}")
        print(f"    {len(acntno)} : {acntno}")
        print(f"    {len(acntnm)} : {acntnm}")
        goog_businfo = gg.goog_get_business_address(instut)
        has_businfo  = True if len(goog_businfo) > 0 else False
        print(f"{instut} got business info of {len(goog_businfo)}")

        if has_businfo:
          taddr_hash = zlib.crc32(
                      (goog_businfo.get("street")  +
                       goog_businfo.get("city")    +
                       goog_businfo.get("state")   +
                       str(goog_businfo.get("zipcode")) +
                       goog_businfo.get("country")
                      ).encode("utf-8"))

          #Existing financial address  
          if(taddr_hash not in existing_finaddr):
            existing_finaddr.add(taddr_hash)
            faddr_hash = taddr_hash
            finaddr_cols = [
              "id",
              "location_name",
              "address",
              "city",
              "state",
              "zipcode",
              "country",
              "phoneno"
            ]
            finaddr_vals = [
              faddr_hash,
              goog_businfo.get("busname"),
              goog_businfo.get("street"),
              goog_businfo.get("city"),
              goog_businfo.get("state"),
              goog_businfo.get("zipcode"),
              goog_businfo.get("country"),
              ""
            ]
            finaddr_addrows_list.append({k: v for k,v in zip(finaddr_cols,finaddr_vals)})

          else: faddr_hash = taddr_hash #Remember to set faddr to the existing hash...


        date_str = datetime.now().strftime("%m-%d-%Y")
        type_str = "BANK" if ("BANKS" == spreadsheet_ky) else "CCARD"

        finst_cols = [
            "id",              #fininst_addrow[col] = fina_hash
            "type",            #fininst_addrow[col] = type_str
            "institution",     #fininst_addrow[col] = instut
            "accnumb_abrv",    #fininst_addrow[col] = acntno 
            "account_desc",    #fininst_addrow[col] = acntnm 
            "routing_numb",    #fininst_addrow[col] = acntnm 
            "account_numb",    #fininst_addrow[col] = acntnm 
            "balance",         #fininst_addrow[col] = 0.00
            "interest_rate",   #fininst_addrow[col] = 0.00
            "expiration_date", #fininst_addrow[col] = date_str 
            "addr_id"          #fininst_addrow[col] = faddr_hash
        ]
        finst_vals = [
            fina_hash,
            type_str,
            instut,
            acntno,
            acntnm,
            "",
            "",
            0.00,
            0.00,
            date_str,
            faddr_hash
        ]
        fininst_addrows_list.append({k: v for k,v in zip(finst_cols,finst_vals)})

     #---End of for loop 
     #================================================================

     #If there are last remaining left over to add...
     if(len(vendors_addrows_list ) > 0): add_vend_db()
     if(len(fininst_addrows_list ) > 0): add_fina_db()
     #else:
     # print(f"\nNo new vendors. Nothing to insert into the database.\n")

  except HttpError as err:
    print(err)

  print(f"---finished with existing Vendors: {len(existing_vendors)}")
  print(f"---finished with existing Finance: {len(existing_fininst)}")
  print(f"-- Done building from the {spreadsheet_ky} spreadsheet.")
  print(f"--")
#========================================================================

"""
 ------------------------------------------------------------------------
  Query a table's contents from the database
 ------------------------------------------------------------------------
"""
def query_table_contents(table_name = "vendors"):
  """ Query a table from the database contents

    Args:
       table_name: The name of the table to query

    Returns:
        True if success False if failure

    Raises:
        Nothing
  """
  print(f"Begin querying the {table_name} table...")

  print(f"  Creating database engine {SQA_URL}...")
  sqa_engine = create_engine(SQA_URL)
  print(f"  Created database engine.\n")

  #Check for existence of the given tablename in database.
  sqa_inspect = inspect(sqa_engine)
  db_tables   = sqa_inspect.get_table_names()

  if(table_name not in db_tables):
    print(f"ERROR: Given table name \"{table_name}\" does not exist in database tables {db_tables}")
    return False
  
  #print(f"table names\n {db_tables}")
  #if(1):sys.exit(0)


  db_table = SQA.Table(table_name, SQA.MetaData(),autoload_with=sqa_engine)
  db_table_hdrs = db_table.columns.keys()


  with sqa_engine.connect() as sqa_conn:
    #Query the vendors table
    print(f"Querying the {table_name} table...")
    sqa_result = sqa_conn.execute(SQA.select(db_table)).fetchall()
    print(f"Queried {len(sqa_result)} rows from the {table_name} table.")
    print(f"{table_name} columns:\n{db_table_hdrs}")
    print(f"------------------------------------------------------------")
    for sqa_row in sqa_result:
      print(sqa_row)
#======================================================================

"""
 ------------------------------------------------------------------------
  Test a database table's contents.
 ------------------------------------------------------------------------
"""
def test_table_contents(table_name = "vendors"):
  """ Query a table from the database contents

    Args:
       table_name: The name of the table to query

    Returns:
        True if success False if failure

    Raises:
        Nothing
  """
  print(f"Begin test {table_name} table...")

  print(f"  Creating database engine {SQA_URL}...")
  sqa_engine = create_engine(SQA_URL)
  print(f"  Created database engine.\n")

  #Check for existence of the given tablename in database.
  sqa_inspect = inspect(sqa_engine)
  db_tables   = sqa_inspect.get_table_names()

  if(table_name not in db_tables):
    print(f"ERROR: Given table name \"{table_name}\" does not exist in database tables {db_tables}")
    return False
  
  db_table = SQA.Table(table_name, SQA.MetaData(),autoload_with=sqa_engine)

  #db_table_hdrs = db_table.columns.keys()

  sqa_stmt = SQA.select(db_table.c.id)
  with sqa_engine.connect() as sqa_conn:
    print(f"Querying the {table_name} table...")
    sqa_result = sqa_conn.scalars(sqa_stmt).all()
    print(f"Queried {len(sqa_result)} rows from the {table_name} table.")
    print(sqa_result)
    #print(f"{table_name} columns:\n{db_table_hdrs}")

  return True
  """_summary_
  with sqa_engine.connect() as sqa_conn:
    #Query the vendors table
    print(f"Querying the {table_name} table...")
    sqa_result = sqa_conn.execute(SQA.select(db_table)).fetchall()
    print(f"Queried {len(sqa_result)} rows from the {table_name} table.")
    print(f"{table_name} columns:\n{db_table_hdrs}")
    print(f"------------------------------------------------------------")
    for sqa_row in sqa_result:
      print(sqa_row)
  """
#======================================================================


"""
------------------------------------------------------------------------
   Read and execute the sql script file on the database.
------------------------------------------------------------------------
"""
def execute_sql_script(sql_fname):
  """Execute a file sql commands on the database 

    Args:
       sql_fname: The name of the sql file script to run

    Returns:
        True if success False if failure

    Raises:
        Nothing
  """
  print(f"Executing sql script {sql_fname} on the database.")

  #open the SQL script file and read its contents  
  try:
    with open(sql_fname, "r", encoding="utf-8") as sql_file:
      sql_script    = sql_file.read()
      sql_statements = sql_script.split(";")
      if(0  == len(sql_statements)):
        print(f"ERROR: file {sql_fname} does not contain any sql statements")
        return False
  except FileNotFoundError:
    print(f"ERROR: file {sql_fname} does not exist")
    return False


  #Create a database engine using SQLAlchemy
  print(f"Creating database engine {SQA_URL}...")
  sqa_engine = create_engine(SQA_URL)
  print(f"Created database engine")

  #Execute the sql statements on the database
  with sqa_engine.connect() as sqa_conn:
    print(f"Executing sql statments on engine.\n")
    for sql_stmt in sql_statements:
      sql_stmt = sql_stmt.strip()
      if(len(sql_stmt) > 0): 
        print(f"Executing sql statement: {sql_stmt}\n")
        # Execute the SQL statement on the database
        sqa_conn.execute(text(sql_stmt))
        sqa_conn.commit()  # Commit the changes if it's a modifying statement
        print(f"Statement executed successfully.\n")

  print(f"\nExecuted sql script.")
  return True
#===========================================================================

"""
  -------------------------------------------------------------------------
   Create command line options 
  -------------------------------------------------------------------------
"""
def create_cmdline_parser():
    """Create command line parser 

    Args:
        None

    Returns:
        An instance of optparse OptionParser

    Raises:
        Nothing
    """
    usage = "usage: %prog spreadsheet[BANKS|CCARD|CITIBANK] [options]"
    p = optparse.OptionParser(usage=usage)

    p.add_option("-r","--run_sql",
                 dest="sql_fname",
                 action="store",
                 help="Execute the sql script file on the database."
                )
    p.add_option("-a","--all_spreadsheets",
                 dest="all_sprshts",
                 action="store_true",
                 default=False,
                 help="Read from all the Tiller spreadsheets"
                )
    p.add_option("-q","--query_table",
                 dest="qry_tname",
                 action="store",
                 help="Query a database table contents."
                )
    p.add_option("-t","--test_table",
                 dest="tst_table",
                 action="store",
                 help="Test a database table contents."
                )
    p.add_option("-b","--build_vendors",
                 dest="bld_vendors",
                 action="store_true",
                 default=False,
                 help="Build the vendors table from the given spreadsheet."
                )
    
    return p
#===========================================================================

"""
  -------------------------------------------------------------------------
   Main function  
  -------------------------------------------------------------------------
"""
if __name__ == "__main__":

    opts,args = create_cmdline_parser().parse_args()

    if (0     == len(args))        and \
       (None  == opts.sql_fname)   and \
       (None  == opts.qry_tname)   and \
       (None  == opts.tst_table)   and \
       (False == opts.all_sprshts) and \
       (False == opts.bld_vendors): 
       print("Error must specify action. Type -h for usage")
       sys.exit(1)

    spsht_name = ""
    
    r_q_t  = True if ((None  != opts.sql_fname) or
                      (None  != opts.qry_tname) or
                      (None  != opts.tst_table)) else False
    if(not r_q_t):
      if (len(args) < 1) and not opts.all_sprshts:
       print("Error: Must specify spreadsheet name or use -all_spreadsheets option. Type -h for usage")
       sys.exit(1)
      elif (len(args) > 0) and opts.all_sprshts:
       print("Error: Either specify spreadsheet name or use -all_spreadsheets option. Type -h for usage")
       sys.exit(1)
      elif (len(args) > 0):
       spsht_name = args[0].upper()
       if(spsht_name not in TILLER_SPRSH_DICT):
         print(f"Error invalid spreadsheet name {spsht_name}. Type -h for usage")
         sys.exit(1)
       else:
         print(f"Spreadsheet name : {spsht_name}")

    if((0     != len(args))         or  \
       (True  == opts.all_sprshts)) and r_q_t:
        print(f"Error: Do not specify spreadsheet name or -a option with -r or -q or -t option. Type -h for usage")
        sys.exit(1)

    #Initialize the Google information
    gg.goog_init()

    #Query Table
    if(opts.qry_tname):
      query_table_contents(opts.qry_tname)

    #Test table
    elif(opts.tst_table):
      test_table_contents(opts.tst_table)

    #Run a sql file name
    elif(opts.sql_fname):
      execute_sql_script(opts.sql_fname)

    #Build vendor tables
    elif(opts.bld_vendors):
        if(0 != len(spsht_name)):
          build_db_from_sprsht(spsht_name,TILLER_SPRSH_DICT[spsht_name])
        elif (opts.all_sprshts):
          for spx,(spsht_nm,spsht_id) in enumerate(TILLER_SPRSH_DICT.items()):
            print(f"!!!")
            print(f"!!! ======================================================")
            print(f"!!! Building from spreadsheet name : {spsht_nm}")
            print(f"!!! ======================================================")
            print(f"!!!")
            build_db_from_sprsht(spsht_nm,spsht_id)

    else:
        print("Unsupported option")