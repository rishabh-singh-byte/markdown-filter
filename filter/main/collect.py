"""
Document Data Collector
========================
Collects all document analysis data using check_markdown.py functions.
Returns raw JSON dictionary with all parameters collected.
"""

# =============================================================================
#                           IMPORTS
# =============================================================================

import json
import sys
import os
from typing import Dict, Any

# Add current directory to path to import check_markdown
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Add parent directory to path to import table_logic
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from check_markdown import (
    html_to_markdown,
    extract_tables_from_markdown,
    analyze_table_content,
    find_links_images,
    analyze_markdown_structure,
    summarize_document,
)

from table_logic import is_table_gibberish

# =============================================================================
#                           CONFIGURATION PARAMETERS
# =============================================================================

DEFAULT_DATA_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/data/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 2000

# =============================================================================
#                           CORE FUNCTIONS
# =============================================================================

def collect_document_data(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collect all document analysis data using check_markdown.py functions.
    
    Args:
        doc: Document dictionary with 'body', 'id', 'title', 'url' fields
    
    Returns:
        Dictionary with complete raw document analysis data including:
        - Document metadata (id, title, url)
        - Markdown conversion
        - Table data (raw tables and analysis)
        - Text scan results
        - Structure analysis
        - Word counts
        - All metrics and statistics
    """
    # Get HTML body
    html_body = doc.get("body", "")
    
    # Convert to markdown
    markdown_content = html_to_markdown(html_body)
    
    # Extract tables
    tables = extract_tables_from_markdown(markdown_content)
    
    # Analyze each table
    table_summaries = []
    for table_idx, table in enumerate(tables):
        table_analysis = analyze_table_content(table)
        table_summaries.append({
            "table_index": table_idx,
            "raw_table": table,  # Include raw table data
            "analysis": table_analysis
        })
    
    # Scan text for links, images, files, mentions
    text_scan = find_links_images(markdown_content)
    
    # Analyze markdown structure
    structure = analyze_markdown_structure(markdown_content)
    
    # Calculate word counts safely
    # NOTE: total_word_count from analyze_markdown_structure already excludes tables, headings, and metadata
    total_word_count = structure.get("word_count", 0)
    table_word_count = sum(t["analysis"].get("words", 0) for t in table_summaries) if table_summaries else 0
    table_meaningful_words = sum(t["analysis"].get("meaningful_words", 0) for t in table_summaries) if table_summaries else 0
    table_placeholder_words = sum(t["analysis"].get("placeholder_words", 0) for t in table_summaries) if table_summaries else 0
    # Since total_word_count already excludes tables, no need to subtract again
    word_count_excluding_tables = total_word_count
    
    # Context-aware table quality decisions (for small key-value table handling)
    # Extract all table analyses for context
    all_table_analyses = [t["analysis"] for t in table_summaries]
    useful_count = 0
    gibberish_count = 0
    
    for idx, table_summary in enumerate(table_summaries):
        # Use context-aware decision with optional parameters
        is_gibberish, decision_info = is_table_gibberish(
            table_summary["analysis"],
            all_tables=all_table_analyses,
            current_table_index=idx
        )
        
        if is_gibberish:
            gibberish_count += 1
        else:
            useful_count += 1
    
    # Collect all data
    collected_data = {
        # Document metadata
        "id": doc.get("id"),
        "title": doc.get("title"),
        "url": doc.get("url"),
        
        # Raw content
        # "html_body": html_body,
        # "markdown_content": markdown_content,
        
        # Table data
        "num_tables": len(tables),
        "tables": table_summaries,
        
        # Table aggregated metrics
        "table_images_count": sum(t["analysis"].get("images", 0) for t in table_summaries) if table_summaries else 0,
        "table_mentions_count": sum(t["analysis"].get("mentions", 0) for t in table_summaries) if table_summaries else 0,
        "table_links_count": sum(t["analysis"].get("links", 0) for t in table_summaries) if table_summaries else 0,
        "table_files_count": sum(t["analysis"].get("files", 0) for t in table_summaries) if table_summaries else 0,
        "table_word_count": table_word_count,
        "table_meaningful_words": table_meaningful_words,
        "table_placeholder_words": table_placeholder_words,
        
        # Word counts
        "total_word_count": total_word_count,
        "word_count_excluding_tables": word_count_excluding_tables,
        
        # Text scan results (links, images, files, mentions in entire document)
        "link_count": text_scan.get("links", 0),
        "image_count": text_scan.get("images", 0),
        "file_ref_count": text_scan.get("file_refs", 0),
        "mention_count": text_scan.get("mentions", 0),
        
        # Structure analysis
        "structure_summary": structure,
        
        # Additional metadata
        "has_tables": len(tables) > 0,
        "has_empty_tables": any(t["analysis"].get("is_empty_table", True) for t in table_summaries) if table_summaries else False,
        "has_useful_tables": useful_count > 0 if table_summaries else False,
        "useful_table_count": useful_count if table_summaries else 0,
        "gibberish_table_count": gibberish_count if table_summaries else 0,
        "total_table_cells": sum(t["analysis"].get("total_cells", 0) for t in table_summaries) if table_summaries else 0,
        "total_filled_cells": sum(t["analysis"].get("filled_cells", 0) for t in table_summaries) if table_summaries else 0,
        "average_table_fill_percentage": (
            round(sum(t["analysis"].get("fill_percentage", 0.0) for t in table_summaries) / len(table_summaries), 2)
            if table_summaries else 0.0
        ),
    }
    
    return collected_data

# =============================================================================
#                           MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    dump_file_name = DEFAULT_DATA_FILE
    try:
        with open(dump_file_name, "r", encoding="utf-8") as f:
            items = [json.loads(line) for line in f if line.strip()]
            if items:
                result = collect_document_data(items[DEFAULT_TEST_INDEX])
                print(result)
            else:
                print("❌ No items found in the JSONL file")
    except FileNotFoundError:
        print(f"❌ File not found: {dump_file_name}")
    except Exception as e:
        print(f"❌ Error processing file: {e}")