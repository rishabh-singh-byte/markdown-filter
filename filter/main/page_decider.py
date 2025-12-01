"""
Page Gibberish Decider
=======================
Page-level analysis to determine if a Confluence page is useful or gibberish.
Uses table analysis from table_logic.py and content metrics from collect.py.
"""

# =============================================================================
#                           IMPORTS
# =============================================================================

import json
import sys
import os

# Add parent directory to path to import table_logic
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from filter.main.collect import collect_document_data
from table_logic import is_table_gibberish

# =============================================================================
#                           CONFIGURATION PARAMETERS
# =============================================================================

DEFAULT_DATA_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/data/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 10131
# DEFAULT_TEST_PAGE_ID = 2198077443
WORDS_OUTSIDE_TABLES_THRESHOLD = 30

# =============================================================================
#                           CORE FUNCTIONS
# =============================================================================

def is_page_gibberish(doc_data):
    """
    Determine if a page is gibberish based on meaningful content (excluding headings).
    
    Decision Criteria (ANY of these makes the page USEFUL):
    1. At least one useful table is present
    2. Content outside tables (excluding headings) contains:
       - Meaningful word count >= 10 (words outside tables, excluding headings)
       - Links (outside tables)
       - Images (outside tables)
       - File references (outside tables)
       - User mentions (outside tables)
    
    Args:
        doc_data: Document data dictionary from collect_document_data()
    
    Returns:
        bool: True if gibberish, False if useful
        dict: Decision breakdown with reasons
    """
    if not doc_data:
        return True, {"reason": "Empty or invalid document data"}
    
    # Check for useful tables
    useful_table_count = doc_data.get('useful_table_count', 0)
    has_useful_tables = useful_table_count > 0
    
    # Calculate content metrics outside tables (excluding headings)
    # word_count already excludes headings, word_count_excluding_tables excludes both headings and tables
    words_outside_tables = doc_data.get('word_count_excluding_tables', 0)
    
    # Total document metrics
    total_links = doc_data.get('link_count', 0)
    total_images = doc_data.get('image_count', 0)
    total_files = doc_data.get('file_ref_count', 0)
    total_mentions = doc_data.get('mention_count', 0)
    
    # Table-specific metrics
    table_links = doc_data.get('table_links_count', 0)
    table_images = doc_data.get('table_images_count', 0)
    table_files = doc_data.get('table_files_count', 0)
    table_mentions = doc_data.get('table_mentions_count', 0)
    
    # Content outside tables
    links_outside_tables = max(0, total_links - table_links)
    images_outside_tables = max(0, total_images - table_images)
    files_outside_tables = max(0, total_files - table_files)
    mentions_outside_tables = max(0, total_mentions - table_mentions)
    
    # Track reasons for decision
    useful_indicators = []
    
    # Check useful tables
    if has_useful_tables:
        useful_indicators.append(f"{useful_table_count} useful table(s)")
    
    # Check words outside tables (excluding headings)
    if words_outside_tables >= WORDS_OUTSIDE_TABLES_THRESHOLD:
        useful_indicators.append(f"{words_outside_tables} words outside tables (excl. headings)")
    
    # Check links outside tables
    if links_outside_tables > 0:
        useful_indicators.append(f"{links_outside_tables} link(s) outside tables")
    
    # Check images outside tables
    if images_outside_tables > 0:
        useful_indicators.append(f"{images_outside_tables} image(s) outside tables")
    
    # Check file references outside tables
    if files_outside_tables > 0:
        useful_indicators.append(f"{files_outside_tables} file reference(s) outside tables")
    
    # Check user mentions outside tables
    if mentions_outside_tables > 0:
        useful_indicators.append(f"{mentions_outside_tables} user mention(s) outside tables")
    
    # Decision logic
    is_gibberish = len(useful_indicators) == 0
    
    decision_info = {
        "is_gibberish": is_gibberish,
        "useful_table_count": useful_table_count,
        "gibberish_table_count": doc_data.get('gibberish_table_count', 0),
        "total_tables": doc_data.get('num_tables', 0),
        "words_outside_tables": words_outside_tables,
        "links_outside_tables": links_outside_tables,
        "images_outside_tables": images_outside_tables,
        "files_outside_tables": files_outside_tables,
        "mentions_outside_tables": mentions_outside_tables,
        "useful_indicators": useful_indicators,
        "reason": "No useful content found" if is_gibberish else f"Useful: {', '.join(useful_indicators)}"
    }
    
    return is_gibberish, decision_info

# =============================================================================
#                           MAIN EXECUTION
# =============================================================================

def main():
    """
    Main function to analyze a page and display results.
    Usage: python page_decider.py [dump_file] [index]
    """
    # Accept command-line arguments: python page_decider.py [dump_file] [index]
    if len(sys.argv) >= 3:
        dump_file_name = sys.argv[1]
        index = int(sys.argv[2])
    elif len(sys.argv) == 2:
        dump_file_name = DEFAULT_DATA_FILE
        index = int(sys.argv[1])
    else:
        dump_file_name = DEFAULT_DATA_FILE
        index = DEFAULT_TEST_INDEX
        # page_id = DEFAULT_TEST_PAGE_ID

    with open(dump_file_name, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f):
            if line_number != index:
                continue  # skip lines until the desired index

            

            data = json.loads(line)
            doc_id = data.get("id")
            doc_data = collect_document_data(data)

            # print(f"Page {index}")
            
            # === PAGE-LEVEL ANALYSIS ===
            print("="*80)
            print("📄 PAGE ANALYSIS")
            print(f"Page {index}")
            print("="*80)
            print(f"URL: {doc_data['url']}")
            print(f"Title: {doc_data['title']}")
            print(f"Document ID: {doc_id}")
            
            # Analyze page
            page_is_gibberish, page_info = is_page_gibberish(doc_data)
            page_status = "❌ GIBBERISH PAGE" if page_is_gibberish else "✅ USEFUL PAGE"
            
            print(f"\n{page_status}")
            print(f"Decision: {page_info['reason']}")
            print(f"\nPage Metrics:")
            print(f"  📊 Tables:")
            print(f"    • Total: {page_info['total_tables']}")
            print(f"    • Useful: {page_info['useful_table_count']}")
            print(f"    • Gibberish: {page_info['gibberish_table_count']}")
            print(f"  📝 Content Outside Tables (excl. headings):")
            print(f"    • Words: {page_info['words_outside_tables']}")
            print(f"    • Links: {page_info['links_outside_tables']}")
            print(f"    • Images: {page_info['images_outside_tables']}")
            print(f"    • Files: {page_info['files_outside_tables']}")
            print(f"    • Mentions: {page_info['mentions_outside_tables']}")
            
            # === TABLE-LEVEL ANALYSIS ===
            tables = doc_data.get('tables', [])
            if tables:
                print(f"\n{'='*80}")
                print(f"📋 TABLE DETAILS ({len(tables)} table(s))")
                print(f"{'='*80}\n")
                
                # Extract all table analyses for context-aware processing
                all_table_analyses = [table.get('analysis', {}) for table in tables]
                
                for idx, table in enumerate(tables):
                    table_index = table.get('table_index')
                    # Use context-aware decision for small key-value table handling
                    # Pass optional context parameters to is_table_gibberish()
                    is_gibberish, decision_info = is_table_gibberish(
                        table.get('analysis', {}),
                        all_tables=all_table_analyses,
                        current_table_index=idx
                    )
                    status = "❌ Gibberish" if is_gibberish else "✅ Useful"
                    
                    # Show if this is a small key-value table
                    is_small_kv = decision_info.get('is_small_key_value', False)
                    kv_marker = " [Small KV ≤4 rows]" if is_small_kv else ""
                    
                    print(f"Table {table_index} is {status}{kv_marker}")
                    print(f"  Decision: {decision_info['reason']}")
                    print(f"  Metrics:")
                    print(f"    • Meaningful Words: {decision_info['meaningful_words']} (excl. headings & placeholders)")
                    print(f"    • Total Words: {decision_info['total_words']} (excl. headings)")
                    print(f"    • Placeholder Words: {decision_info['placeholder_words']}")
                    print(f"    • Links: {decision_info['links']}")
                    print(f"    • Images: {decision_info['images']}")
                    print(f"    • Files: {decision_info['files']}")
                    print(f"    • Mentions: {decision_info['mentions']}")
                    
                    print("\n  Table Content:")
                    for row in table.get('raw_table', []):
                        print(f"    {row}")
                    print("\n" + "="*80 + "\n")
            else:
                print(f"\n{'='*80}")
                print(f"📋 No tables found in this document")
                print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

