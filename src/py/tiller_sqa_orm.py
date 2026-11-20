"""
============================================================
      The SQLAlchemy ORM classes for the tiller data reader.
============================================================
"""

from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


"""
 ------------------------------------------------------------------------
  Show the vendors addresses obtained from googlemaps
 ------------------------------------------------------------------------
def add_gmap_addresses():
  print(f"Begin building the googlemap addresses...")

  print(f"  Creating database engine {SQA_URL}...")
  sqa_engine = create_engine(SQA_URL)
  print(f"  Created database engine.\n")

  vendors_table = SQA.Table("vendors", SQA.MetaData(),autoload_with=sqa_engine)
  vendors_hdrs  = vendors_table.columns.keys()

  idx           = 0
  shrt_desc_idx = 0
  full_desc_idx = 0

  for idx,hdr in enumerate(vendors_hdrs):
    #print(f"{idx}\t{hdr}")
    match hdr:
      case "shrt_desc": shrt_desc_idx = idx
      case "full_desc": full_desc_idx = idx

  print(f"shrt_desc_idx : {shrt_desc_idx} full_desc_idx : {full_desc_idx}")
  with sqa_engine.connect() as sqa_conn:
    bus_req_payload = {
      "textQuery": ""
    }

    sqa_result = sqa_conn.execute(SQA.select(vendors_table)).fetchall()
    #print(f"Queried {len(sqa_result)} rows from the vendors table.")
    for idx,sqa_row in enumerate(sqa_result):
      print(f"{idx}\t{sqa_row[shrt_desc_idx]}")
      bus_name_abrv = sqa_row[shrt_desc_idx]
      gg.goog_get_business_address(bus_name_abrv)
      if(10 == idx): sys.exit(0)

"""

"""
 --------------------------------------------------------------------
  Read the header of the tiller transactions spreadsheet 
  and return a list of column names.
 --------------------------------------------------------------------
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
#===========================================================================