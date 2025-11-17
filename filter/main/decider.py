"""
Simple Page and Table Decider Test Script
==========================================
Tests page and table gibberish detection on a specific document by page ID and URL.
"""

# =============================================================================
#                           IMPORTS
# =============================================================================

import json
import sys
import os

# Add parent directory to path to import table_logic
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from page_decider import is_page_gibberish
from table_logic import is_table_gibberish
from collect import collect_document_data

# =============================================================================
#                           CONFIGURATION PARAMETERS
# =============================================================================

DEFAULT_DATA_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/data/confluence_markdown.jsonl"
DEFAULT_PAGE_ID = 2693925455
DEFAULT_URL = "https://simpplr.atlassian.net/wiki/spaces/OPS/pages/2693925455/2021+-+Release+Cycle+Dates"

# =============================================================================
#                           MAIN EXECUTION
# =============================================================================

def main():
    dump_file_name = DEFAULT_DATA_FILE
    page_id = DEFAULT_PAGE_ID
    url = DEFAULT_URL


    with open(dump_file_name, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f):
            data = json.loads(line)
            if str(data.get("id")) != str(page_id) or data.get("url") != url:
                continue

            # Extract parameters from data fields
            doc_id = data.get("id")
            
            print(f"Processing document:")
            print(f"  URL: {url}")
            print(f"  ID: {doc_id}")

            doc_data = collect_document_data(data)
            page_is_gibberish, page_info = is_page_gibberish(doc_data)
            # table_is_gibberish, table_info = is_table_gibberish(doc_data)

            print(f"\nPage {doc_id} is gibberish: {page_is_gibberish}")
            page_status = "❌ GIBBERISH PAGE" if page_is_gibberish else "✅ USEFUL PAGE"
            print(f"{page_status}")
            print(f"Decision: {page_info['reason']}")
            # print(f"Table {page_id} is gibberish: {table_is_gibberish}")

if __name__ == "__main__":
    main()