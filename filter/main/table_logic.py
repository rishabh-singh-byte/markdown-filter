"""
Table Logic Analyzer - Priority-Based Decision System with Size-Adaptive Analysis
==================================================================================
Analyzes table quality using priority-based checks and size-adaptive output.

Table Size Categories:
1. VERY_SMALL: n × 2 (Key-Value tables)
   - Special analysis of 2nd column (values)
   - Focus on fill percentage and word count of values column
   
2. SMALL: 2-5 rows OR 2-5 columns
   - Simplified analysis with essential metrics
   - Row-wise summary of fill and word counts
   
3. MEDIUM: 6-15 rows AND 6-15 columns
   - Detailed analysis with all structural checks
   - Full row-wise content breakdown
   
4. LARGE: >15 rows OR >15 columns
   - Comprehensive detailed analysis
   - All structural checks and header analysis

Priority Order (Same for all sizes):
1. Links > Files > Images > Mentions (High Priority - Useful)
2. Word count > 5 in single cell (Useful)
3. Structural issues (Gibberish indicators):
   - 1st row only filled (empty data rows)
   - 1st column only filled
   - Header-heavy table (>70% content in header - "heading in column only" pattern)
   - Single row/column filled anywhere
4. Meaningful content threshold
5. Fill percentage (Supporting metric)

Decision Flow:
1. Check high-priority items first (links, files, etc.)
2. Check structural gibberish patterns
3. Check meaningful content
4. Make final decision
"""

import json
import sys
import os
from typing import Dict, Any, List, Tuple

# Add filter/main to path (import moved to main() to avoid circular dependency)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'filter', 'main'))

# =============================================================================
#                           CONFIGURATION
# =============================================================================

DATA_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/data/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 6933

# Decision thresholds
MEANINGFUL_WORDS_THRESHOLD = 3
WORDS_PER_CELL_USEFUL = 5  # Single cell with >5 words is useful

# =============================================================================
#                           PRIORITY 1: HIGH-VALUE CONTENT CHECKS
# =============================================================================

def check_priority_content(analysis: Dict[str, Any]) -> Tuple[bool, str, Dict[str, int]]:
    """
    Check high-priority content (links > files > images > mentions).
    If any found, table is likely USEFUL.
    
    Returns:
        (has_priority_content, reason, counts_dict)
    """
    links = analysis.get('links', 0)
    files = analysis.get('files', 0)
    images = analysis.get('images', 0)
    mentions = analysis.get('mentions', 0)
    
    counts = {'links': links, 'files': files, 'images': images, 'mentions': mentions}
    
    # Priority order: Links > Files > Images > Mentions
    if links > 0:
        return True, f"{links} link(s) found (highest priority)", counts
    if files > 0:
        return True, f"{files} file(s) found (high priority)", counts
    if images > 0:
        return True, f"{images} image(s) found", counts
    if mentions > 0:
        return True, f"{mentions} user mention(s) found", counts
    
    return False, "No priority content", counts


def check_cell_word_count(analysis: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Check if any single cell has > 5 meaningful words (indicates useful content).
    
    Returns:
        (has_rich_cell, reason)
    """
    cell_grid = analysis.get('cell_metrics_grid', [])
    
    for row_idx, row in enumerate(cell_grid):
        if row_idx == 0:  # Skip header
            continue
        
        for cell in row:
            meaningful_words = cell.get('meaningful_words', 0)
            if meaningful_words > WORDS_PER_CELL_USEFUL:
                return True, f"Found cell with {meaningful_words} meaningful words (>5 threshold)"
    
    return False, "No cell has >5 meaningful words"


# =============================================================================
#                           STRUCTURAL GIBBERISH CHECKS
# =============================================================================

def check_first_row_only_filled(analysis: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Check if only first row (header) is filled and all data rows are empty.
    Strong gibberish indicator.
    """
    per_row = analysis.get('per_row_summaries', [])
    rows = analysis.get('rows', 0)
    
    if rows <= 1:
        return False, f"Only {rows} row total"
    
    # Count data rows with content
    filled_data_rows = 0
    for i, row_summary in enumerate(per_row):
        if i == 0:  # Skip header
            continue
        
        meaningful_words = row_summary.get('meaningful_words', 0)
        links = row_summary.get('links', 0)
        
        if meaningful_words > 0 or links > 0:
            filled_data_rows += 1
    
    if filled_data_rows == 0:
        return True, f"Only header row filled, {rows - 1} data rows empty"
    
    return False, f"{filled_data_rows}/{rows - 1} data rows have content"


def check_first_column_only_filled(analysis: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Check if only first column is filled.
    Gibberish indicator.
    """
    cell_grid = analysis.get('cell_metrics_grid', [])
    cols = analysis.get('cols', 0)
    
    if cols <= 1:
        return False, f"Only {cols} column total"
    
    # Count columns with content (excluding header row)
    col_has_content = [False] * cols
    
    for row_idx, row in enumerate(cell_grid):
        if row_idx == 0:  # Skip header
            continue
        
        for col_idx, cell in enumerate(row):
            if col_idx >= cols:
                break
            
            meaningful_words = cell.get('meaningful_words', 0)
            if meaningful_words > 0:
                col_has_content[col_idx] = True
    
    filled_cols = sum(col_has_content)
    
    if filled_cols == 1 and col_has_content[0]:
        return True, f"Only 1st column filled, {cols - 1} other columns empty"
    
    return False, f"{filled_cols}/{cols} columns have content"


def check_single_row_or_column_filled(analysis: Dict[str, Any]) -> Tuple[bool, str, Dict]:
    """
    Check if only ONE row or ONE column is filled (not necessarily first).
    Gibberish indicator.
    """
    cell_grid = analysis.get('cell_metrics_grid', [])
    rows = analysis.get('rows', 0)
    cols = analysis.get('cols', 0)
    
    if rows <= 1 or cols <= 1:
        return False, "Too small to check", {}
    
    # Check rows (excluding header)
    rows_with_content = []
    for row_idx, row in enumerate(cell_grid):
        if row_idx == 0:
            continue
        
        has_content = any(cell.get('meaningful_words', 0) > 0 for cell in row)
        if has_content:
            rows_with_content.append(row_idx)
    
    # Check columns
    cols_with_content = []
    for col_idx in range(cols):
        has_content = False
        for row_idx, row in enumerate(cell_grid):
            if row_idx == 0:
                continue
            if col_idx < len(row) and row[col_idx].get('meaningful_words', 0) > 0:
                has_content = True
                break
        if has_content:
            cols_with_content.append(col_idx)
    
    total_data_rows = rows - 1
    
    details = {
        'filled_rows': len(rows_with_content),
        'total_data_rows': total_data_rows,
        'filled_cols': len(cols_with_content),
        'total_cols': cols
    }
    
    if len(rows_with_content) == 1:
        return True, f"Only 1 row filled (row {rows_with_content[0]}), {total_data_rows - 1} rows empty", details
    
    if len(cols_with_content) == 1:
        return True, f"Only 1 column filled (col {cols_with_content[0]}), {cols - 1} columns empty", details
    
    return False, f"{len(rows_with_content)} rows and {len(cols_with_content)} columns have content", details


def count_empty_rows_and_columns(analysis: Dict[str, Any]) -> Dict[str, int]:
    """
    Count fully empty rows and columns (excluding header row).
    """
    cell_grid = analysis.get('cell_metrics_grid', [])
    rows = analysis.get('rows', 0)
    cols = analysis.get('cols', 0)
    
    # Count empty rows (excluding header)
    empty_rows = 0
    for row_idx, row in enumerate(cell_grid):
        if row_idx == 0:
            continue
        
        is_empty = all(cell.get('meaningful_words', 0) == 0 for cell in row)
        if is_empty:
            empty_rows += 1
    
    # Count empty columns
    empty_cols = 0
    for col_idx in range(cols):
        is_empty = True
        for row_idx, row in enumerate(cell_grid):
            if row_idx == 0:
                continue
            if col_idx < len(row) and row[col_idx].get('meaningful_words', 0) > 0:
                is_empty = False
                break
        if is_empty:
            empty_cols += 1
    
    return {
        'empty_rows': empty_rows,
        'total_data_rows': rows - 1 if rows > 1 else 0,
        'empty_cols': empty_cols,
        'total_cols': cols
    }


def check_header_heavy_table(analysis: Dict[str, Any]) -> Tuple[bool, str, Dict]:
    """
    Check if header row contains disproportionate amount of content.
    This indicates "heading in column only" pattern - strong gibberish indicator.
    
    Returns:
        (is_header_heavy, reason, details_dict)
    """
    per_row = analysis.get('per_row_summaries', [])
    rows = analysis.get('rows', 0)
    
    if rows <= 1 or not per_row:
        return False, "Table too small or no row data", {}
    
    header_words = per_row[0].get('meaningful_words', 0) if len(per_row) > 0 else 0
    data_words = sum(row.get('meaningful_words', 0) for row in per_row[1:])
    total_meaningful = header_words + data_words
    
    if total_meaningful == 0:
        return False, "No meaningful words in table", {}
    
    header_percentage = (header_words / total_meaningful * 100)
    
    details = {
        'header_words': header_words,
        'data_words': data_words,
        'total_words': total_meaningful,
        'header_percentage': round(header_percentage, 1)
    }
    
    # If header has >70% of content, it's likely gibberish
    if header_percentage > 70:
        return True, f"Header has {header_percentage:.1f}% of content ({header_words}/{total_meaningful} words)", details
    
    return False, f"Header has {header_percentage:.1f}% of content (acceptable)", details


# =============================================================================
#                           FILL PERCENTAGE (Excluding Headers)
# =============================================================================

def calculate_fill_percentage(analysis: Dict[str, Any]) -> Tuple[float, Dict]:
    """
    Calculate fill percentage of data cells only (excluding ALL headers).
    Excludes both column headers (first row) and row headers (first column).
    """
    cell_grid = analysis.get('cell_metrics_grid', [])
    rows = analysis.get('rows', 0)
    cols = analysis.get('cols', 0)
    headings = analysis.get('headings', {})
    
    if not headings:
        headings = {}
    
    # Determine which cells are headers
    heading_type = headings.get('heading_type', 'none')
    has_column_headers = heading_type in ['column', 'both']
    has_row_headers = heading_type in ['row', 'both']
    
    if rows <= 1:
        return 0.0, {
            'filled': 0, 
            'total': 0, 
            'percentage': 0.0,
            'reason': 'No data rows (excluding headers)'
        }
    
    # Calculate total data cells (excluding headers)
    data_rows = rows - 1 if has_column_headers else rows
    data_cols = cols - 1 if has_row_headers else cols
    total_data_cells = data_rows * data_cols
    
    if total_data_cells <= 0:
        return 0.0, {
            'filled': 0,
            'total': 0,
            'percentage': 0.0,
            'reason': 'No data cells (table only has headers)'
        }
    
    filled_cells = 0
    
    for row_idx, row in enumerate(cell_grid):
        # Skip column header row
        if has_column_headers and row_idx == 0:
            continue
        
        for col_idx, cell in enumerate(row):
            # Skip row header column
            if has_row_headers and col_idx == 0:
                continue
            
            # Count as filled if has meaningful words or links
            if cell.get('meaningful_words', 0) > 0 or cell.get('links', 0) > 0:
                filled_cells += 1
    
    fill_pct = (filled_cells / total_data_cells * 100) if total_data_cells > 0 else 0.0
    
    return fill_pct, {
        'filled': filled_cells,
        'total': total_data_cells,
        'percentage': round(fill_pct, 1),
        'reason': f"{filled_cells}/{total_data_cells} cells filled ({fill_pct:.1f}%) - excluding headers"
    }


# =============================================================================
#                           PRIORITY-BASED DECISION LOGIC
# =============================================================================

def decide_table_quality(analysis: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Make decision using priority-based checks.
    
    Decision Flow:
    1. Check Priority Content (Links > Files > Images > Mentions) → USEFUL
    2. Check Cell Word Count (>5 words) → USEFUL  
    3. Check Structural Issues → GIBBERISH
    4. Check Meaningful Words → USEFUL or GIBBERISH
    5. Default → CAN'T DECIDE
    """
    if not analysis:
        return "GIBBERISH", {"reason": "No analysis data"}
    
    decision_log = []
    
    # Calculate fill percentage for all decisions (excluding headers)
    fill_pct, fill_details = calculate_fill_percentage(analysis)
    fill_info = f"{fill_details['filled']}/{fill_details['total']} cells ({fill_details['percentage']}%) excluding headers"
    
    # STEP 1: Priority Content Check (Highest Priority)
    has_priority, priority_reason, priority_counts = check_priority_content(analysis)
    decision_log.append(f"Priority Content: {priority_reason}")
    
    if has_priority:
        return "USEFUL", {
            "decision": "USEFUL",
            "reason": priority_reason,
            "fill_info": fill_info,
            "fill_percentage": fill_details['percentage'],
            "priority_counts": priority_counts,
            "decision_log": decision_log
        }
    
    # STEP 2: Cell Word Count Check
    has_rich_cell, cell_reason = check_cell_word_count(analysis)
    decision_log.append(f"Rich Cell: {cell_reason}")
    
    if has_rich_cell:
        return "USEFUL", {
            "decision": "USEFUL",
            "reason": cell_reason,
            "fill_info": fill_info,
            "fill_percentage": fill_details['percentage'],
            "decision_log": decision_log
        }
    
    # STEP 3: Structural Gibberish Checks
    first_row_only, first_row_reason = check_first_row_only_filled(analysis)
    decision_log.append(f"First Row Only: {first_row_reason}")
    
    if first_row_only:
        return "GIBBERISH", {
            "decision": "GIBBERISH",
            "reason": "Only header row filled (rest empty)",
            "fill_info": fill_info,
            "fill_percentage": fill_details['percentage'],
            "decision_log": decision_log
        }
    
    first_col_only, first_col_reason = check_first_column_only_filled(analysis)
    decision_log.append(f"First Column Only: {first_col_reason}")
    
    if first_col_only:
        return "GIBBERISH", {
            "decision": "GIBBERISH",
            "reason": "Only first column filled",
            "fill_info": fill_info,
            "fill_percentage": fill_details['percentage'],
            "decision_log": decision_log
        }
    
    # Check for header-heavy tables (heading in column only pattern)
    header_heavy, header_reason, header_details = check_header_heavy_table(analysis)
    decision_log.append(f"Header Heavy: {header_reason}")
    
    if header_heavy:
        return "GIBBERISH", {
            "decision": "GIBBERISH",
            "reason": header_reason,
            "fill_info": fill_info,
            "fill_percentage": fill_details['percentage'],
            "details": header_details,
            "decision_log": decision_log
        }
    
    single_filled, single_reason, single_details = check_single_row_or_column_filled(analysis)
    decision_log.append(f"Single Row/Col: {single_reason}")
    
    if single_filled:
        return "GIBBERISH", {
            "decision": "GIBBERISH",
            "reason": single_reason,
            "fill_info": fill_info,
            "fill_percentage": fill_details['percentage'],
            "details": single_details,
            "decision_log": decision_log
        }
    
    # STEP 4: Meaningful Words Check
    meaningful_words = analysis.get('meaningful_words', 0)
    decision_log.append(f"Meaningful Words: {meaningful_words}")
    
    if meaningful_words >= MEANINGFUL_WORDS_THRESHOLD:
        return "USEFUL", {
            "decision": "USEFUL",
            "reason": f"{meaningful_words} meaningful words found (≥{MEANINGFUL_WORDS_THRESHOLD} threshold)",
            "fill_info": fill_info,
            "fill_percentage": fill_details['percentage'],
            "decision_log": decision_log
        }
    
    # STEP 5: Check if completely empty
    if meaningful_words == 0:
        return "GIBBERISH", {
            "decision": "GIBBERISH",
            "reason": "No meaningful content found",
            "fill_info": fill_info,
            "fill_percentage": fill_details['percentage'],
            "decision_log": decision_log
        }
    
    # STEP 6: Ambiguous cases
    return "CAN'T DECIDE", {
        "decision": "CAN'T DECIDE",
        "reason": f"Ambiguous: {meaningful_words} words (below threshold) but has some content",
        "fill_info": fill_info,
        "fill_percentage": fill_details['percentage'],
        "decision_log": decision_log
    }


# =============================================================================
#                           SMALL KEY-VALUE TABLE DETECTION
# =============================================================================

def is_small_key_value_table(analysis: Dict[str, Any]) -> bool:
    """
    Check if table is a small key-value table (rows <= 4, 2 columns).
    
    Treats any 2-column table with <= 4 rows as a potential small key-value/metadata table,
    regardless of whether it's explicitly marked as key-value by heading detection.
    
    Args:
        analysis: Table analysis dictionary
    
    Returns:
        bool: True if table is small key-value table (rows <= 4, 2 cols)
    """
    rows = analysis.get('rows', 0)
    cols = analysis.get('cols', 0)
    
    # ANY 2-column table with <= 4 rows is considered a small key-value table
    # These are typically metadata tables (Date, Team, Participants, etc.)
    return cols == 2 and rows <= 4


def decide_table_quality_with_context(
    analysis: Dict[str, Any], 
    all_tables: List[Dict[str, Any]] = None,
    current_table_index: int = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Make table decision with page context for special handling of small key-value tables.
    
    Special Rule for Small Key-Value Tables (rows <= 4, 2 columns):
    1. If page has other (non-key-value) tables:
       - If any other table is USEFUL, mark small key-value as GIBBERISH
       - If only small key-value is filled, mark as GIBBERISH
    2. If page has ONLY small key-value tables:
       - Use normal decision logic (check fill percentage)
    
    Args:
        analysis: Current table analysis dictionary
        all_tables: List of all table analyses on the page (optional)
        current_table_index: Index of current table in all_tables (optional)
    
    Returns:
        tuple: (decision: str, decision_info: dict)
    """
    # Check if this is a small key-value table
    is_small_kv = is_small_key_value_table(analysis)
    
    # If no context provided or not a small key-value table, use standard logic
    if not is_small_kv or all_tables is None:
        return decide_table_quality(analysis)
    
    # We have a small key-value table with page context
    # NEW LOGIC: Check if any tables AFTER this one are useful
    # If all subsequent tables are gibberish, mark this small KV as GIBBERISH
    
    # Get tables that come AFTER the current table
    subsequent_tables = []
    if current_table_index is not None:
        for idx in range(current_table_index + 1, len(all_tables)):
            subsequent_tables.append(all_tables[idx])
    
    # If there are no tables after this one, use normal decision logic
    if not subsequent_tables:
        # This is the last table (or only table)
        # Use normal decision logic (will check fill percentage)
        return decide_table_quality(analysis)
    
    # Check if any subsequent table is useful
    has_useful_subsequent_table = False
    
    for subsequent_tbl in subsequent_tables:
        # Don't apply KV logic recursively - use standard decision
        subsequent_decision, _ = decide_table_quality(subsequent_tbl)
        if subsequent_decision == "USEFUL":
            has_useful_subsequent_table = True
            break
    
    # If NO subsequent tables are useful (all are gibberish or empty),
    # mark this small key-value table as GIBBERISH
    if not has_useful_subsequent_table:
        fill_pct, fill_details = calculate_fill_percentage(analysis)
        fill_info = f"{fill_details['filled']}/{fill_details['total']} cells ({fill_details['percentage']}%) excluding headers"
        
        return "GIBBERISH", {
            "decision": "GIBBERISH",
            "reason": "Small key-value table (≤4 rows) with no useful tables after it",
            "fill_info": fill_info,
            "fill_percentage": fill_details['percentage'],
            "decision_log": ["Small key-value table with only gibberish tables following"]
        }
    
    # If there IS at least one useful table after this KV table,
    # also mark this small KV table as GIBBERISH (it's just metadata)
    fill_pct, fill_details = calculate_fill_percentage(analysis)
    fill_info = f"{fill_details['filled']}/{fill_details['total']} cells ({fill_details['percentage']}%) excluding headers"
    
    return "GIBBERISH", {
        "decision": "GIBBERISH",
        "reason": "Small key-value table (≤4 rows) - metadata table with other tables present",
        "fill_info": fill_info,
        "fill_percentage": fill_details['percentage'],
        "decision_log": ["Small key-value metadata table"]
    }


# =============================================================================
#                           COMPATIBILITY WRAPPER FOR LEGACY INTERFACE
# =============================================================================

def is_table_gibberish(
    table_analysis: Dict[str, Any],
    all_tables: List[Dict[str, Any]] = None,
    current_table_index: int = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Wrapper function for compatibility with table_decider.py interface.
    Uses the advanced priority-based decision system from decide_table_quality().
    
    Now supports optional context parameters for small key-value table handling.
    
    This function is used by page_decider.py and decider.py.
    
    Args:
        table_analysis: Table analysis dictionary from analyze_table_content()
        all_tables: Optional list of ALL table analyses on the page for context-aware decisions
        current_table_index: Optional index of current table in all_tables
    
    Returns:
        tuple: (is_gibberish: bool, decision_info: dict)
            - is_gibberish: True if table is gibberish, False if useful
            - decision_info: Dictionary with decision details including:
                - is_gibberish: bool
                - meaningful_words: int
                - total_words: int
                - placeholder_words: int
                - links: int
                - images: int
                - files: int
                - mentions: int
                - useful_indicators: list of reasons
                - reason: str (main reason for decision)
    """
    if not table_analysis:
        return True, {
            "is_gibberish": True,
            "reason": "Empty or invalid table analysis",
            "meaningful_words": 0,
            "total_words": 0,
            "placeholder_words": 0,
            "links": 0,
            "images": 0,
            "files": 0,
            "mentions": 0,
            "useful_indicators": []
        }
    
    # Use context-aware decision if context is provided
    if all_tables is not None:
        decision, decision_info = decide_table_quality_with_context(
            table_analysis,
            all_tables,
            current_table_index
        )
    else:
        # Call the standard decision system without context
        decision, decision_info = decide_table_quality(table_analysis)
    
    # Extract metrics from analysis
    meaningful_words = table_analysis.get('meaningful_words', 0)
    total_words = table_analysis.get('words', 0)
    placeholder_words = table_analysis.get('placeholder_words', 0)
    links = table_analysis.get('links', 0)
    images = table_analysis.get('images', 0)
    files = table_analysis.get('files', 0)
    mentions = table_analysis.get('mentions', 0)
    
    # Convert decision to boolean
    is_gibberish = (decision == "GIBBERISH")
    
    # Build useful indicators list for compatibility
    useful_indicators = []
    if not is_gibberish:
        if meaningful_words >= MEANINGFUL_WORDS_THRESHOLD:
            useful_indicators.append(f"{meaningful_words} meaningful words (excl. headings & placeholders)")
        if links > 0:
            useful_indicators.append(f"{links} link(s)")
        if images > 0:
            useful_indicators.append(f"{images} image(s)")
        if files > 0:
            useful_indicators.append(f"{files} file reference(s)")
        if mentions > 0:
            useful_indicators.append(f"{mentions} user mention(s)")
    
    # Build compatible decision info
    compatible_info = {
        "is_gibberish": is_gibberish,
        "meaningful_words": meaningful_words,
        "total_words": total_words,
        "placeholder_words": placeholder_words,
        "links": links,
        "images": images,
        "files": files,
        "mentions": mentions,
        "useful_indicators": useful_indicators,
        "reason": decision_info.get("reason", "Unknown"),
        # Include additional info from advanced decision system
        "advanced_decision": decision,
        "fill_info": decision_info.get("fill_info", ""),
        "fill_percentage": decision_info.get("fill_percentage", 0.0),
        # Include small key-value flag
        "is_small_key_value": is_small_key_value_table(table_analysis),
    }
    
    return is_gibberish, compatible_info


def is_table_gibberish_with_context(
    table_analysis: Dict[str, Any],
    all_tables: List[Dict[str, Any]] = None,
    current_table_index: int = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Enhanced wrapper with page context support for small key-value table handling.
    
    This function should be used when processing multiple tables on a page to properly
    handle small key-value tables (rows <= 4, 2 columns) based on page context.
    
    Args:
        table_analysis: Current table analysis dictionary
        all_tables: List of ALL table analyses on the page (optional)
        current_table_index: Index of current table in all_tables (optional)
    
    Returns:
        tuple: (is_gibberish: bool, decision_info: dict)
    """
    if not table_analysis:
        return True, {
            "is_gibberish": True,
            "reason": "Empty or invalid table analysis",
            "meaningful_words": 0,
            "total_words": 0,
            "placeholder_words": 0,
            "links": 0,
            "images": 0,
            "files": 0,
            "mentions": 0,
            "useful_indicators": []
        }
    
    # Call the context-aware decision system
    decision, decision_info = decide_table_quality_with_context(
        table_analysis, 
        all_tables, 
        current_table_index
    )
    
    # Extract metrics from analysis
    meaningful_words = table_analysis.get('meaningful_words', 0)
    total_words = table_analysis.get('words', 0)
    placeholder_words = table_analysis.get('placeholder_words', 0)
    links = table_analysis.get('links', 0)
    images = table_analysis.get('images', 0)
    files = table_analysis.get('files', 0)
    mentions = table_analysis.get('mentions', 0)
    
    # Convert decision to boolean
    is_gibberish = (decision == "GIBBERISH")
    
    # Build useful indicators list for compatibility
    useful_indicators = []
    if not is_gibberish:
        if meaningful_words >= MEANINGFUL_WORDS_THRESHOLD:
            useful_indicators.append(f"{meaningful_words} meaningful words (excl. headings & placeholders)")
        if links > 0:
            useful_indicators.append(f"{links} link(s)")
        if images > 0:
            useful_indicators.append(f"{images} image(s)")
        if files > 0:
            useful_indicators.append(f"{files} file reference(s)")
        if mentions > 0:
            useful_indicators.append(f"{mentions} user mention(s)")
    
    # Build compatible decision info
    compatible_info = {
        "is_gibberish": is_gibberish,
        "meaningful_words": meaningful_words,
        "total_words": total_words,
        "placeholder_words": placeholder_words,
        "links": links,
        "images": images,
        "files": files,
        "mentions": mentions,
        "useful_indicators": useful_indicators,
        "reason": decision_info.get("reason", "Unknown"),
        # Include additional info from advanced decision system
        "advanced_decision": decision,
        "fill_info": decision_info.get("fill_info", ""),
        "fill_percentage": decision_info.get("fill_percentage", 0.0),
        # Context-aware flag
        "is_small_key_value": is_small_key_value_table(table_analysis),
    }
    
    return is_gibberish, compatible_info


# =============================================================================
#                           TABLE SIZE CATEGORIZATION
# =============================================================================

def categorize_table_size(analysis: Dict[str, Any]) -> str:
    """
    Categorize table by size for appropriate analysis.
    
    Categories:
    - VERY_SMALL: n × 2 key-value tables
    - SMALL: 2-5 rows or 2-5 columns
    - MEDIUM: 6-15 rows and 6-15 columns
    - LARGE: >15 rows or >15 columns
    """
    rows = analysis.get('rows', 0)
    cols = analysis.get('cols', 0)
    
    # Very small: Key-value tables (n × 2)
    if cols == 2:
        return "VERY_SMALL"
    
    # Small: 2-5 dimensions
    if (2 <= rows <= 5) or (2 <= cols <= 5):
        return "SMALL"
    
    # Large: >15 rows or columns
    if rows > 15 or cols > 15:
        return "LARGE"
    
    # Medium: everything else (6-15 range)
    return "MEDIUM"


# =============================================================================
#                           OUTPUT FUNCTIONS - BY SIZE
# =============================================================================

def print_analysis_very_small(analysis: Dict[str, Any], decision: str, decision_info: Dict, table_idx: int):
    """Print analysis for very small (key-value) tables (n × 2)."""
    
    # Header
    if decision == "USEFUL":
        emoji = "✅"
    elif decision == "GIBBERISH":
        emoji = "❌"
    else:
        emoji = "⚠️ "
    
    fill_info = decision_info.get('fill_info', 'N/A')
    
    print(f"\n{'─'*80}")
    print(f"🔷 Table {table_idx + 1}: {emoji} {decision} [VERY SMALL - Key-Value Table]")
    print(f"   Reason: {decision_info['reason']}")
    print(f"   Fill: {fill_info}")
    print(f"{'─'*80}")
    
    rows = analysis.get('rows', 0)
    cols = analysis.get('cols', 0)
    
    print(f"\n📐 Table Dimensions:")
    print(f"   • Size: {rows} rows × {cols} columns (Key-Value format)")
    print(f"   • Total Pairs: {rows - 1} (excluding header)")
    
    # Analyze 2nd column (values column) excluding header
    per_row = analysis.get('per_row_summaries', [])
    cell_grid = analysis.get('cell_metrics_grid', [])
    
    if per_row and cell_grid:
        # Get data from 2nd column (index 1) for all data rows
        second_col_filled = 0
        second_col_total_words = 0
        second_col_meaningful_words = 0
        second_col_links = 0
        second_col_images = 0
        second_col_dates = 0
        
        total_data_rows = rows - 1
        
        for row_idx in range(1, len(cell_grid)):  # Skip header row
            if len(cell_grid[row_idx]) > 1:
                cell = cell_grid[row_idx][1]  # Second column
                if cell.get('meaningful_words', 0) > 0 or cell.get('links', 0) > 0:
                    second_col_filled += 1
                second_col_total_words += cell.get('words', 0)
                second_col_meaningful_words += cell.get('meaningful_words', 0)
                second_col_links += cell.get('links', 0)
                second_col_images += cell.get('images', 0)
                second_col_dates += cell.get('dates', 0)
        
        fill_percentage = (second_col_filled / total_data_rows * 100) if total_data_rows > 0 else 0
        
        print(f"\n📊 Values Column Analysis (2nd column, excluding header):")
        print(f"   • Filled Cells: {second_col_filled}/{total_data_rows} ({fill_percentage:.1f}%)")
        print(f"   • Empty Cells: {total_data_rows - second_col_filled}/{total_data_rows}")
        print(f"   • Meaningful Words: {second_col_meaningful_words} (includes {second_col_dates} dates)")
        print(f"   • Total Words: {second_col_total_words}")
        print(f"   • Links: {second_col_links}")
        print(f"   • Images: {second_col_images}")
        print(f"   • Dates: {second_col_dates}")
    
    # Overall content metrics
    meaningful_words = analysis.get('meaningful_words', 0)
    total_words = analysis.get('words', 0)
    
    print(f"\n📋 Overall Content:")
    print(f"   • Total Meaningful Words: {meaningful_words}")
    print(f"   • Total Words: {total_words}")


def print_analysis_small(analysis: Dict[str, Any], decision: str, decision_info: Dict, table_idx: int):
    """Print analysis for small tables (2-5 rows or columns)."""
    
    # Header
    if decision == "USEFUL":
        emoji = "✅"
    elif decision == "GIBBERISH":
        emoji = "❌"
    else:
        emoji = "⚠️ "
    
    fill_info = decision_info.get('fill_info', 'N/A')
    
    print(f"\n{'─'*80}")
    print(f"🔷 Table {table_idx + 1}: {emoji} {decision} [SMALL Table]")
    print(f"   Reason: {decision_info['reason']}")
    print(f"   Fill: {fill_info}")
    print(f"{'─'*80}")
    
    rows = analysis.get('rows', 0)
    cols = analysis.get('cols', 0)
    total_cells = rows * cols
    data_rows = rows - 1 if rows > 1 else 0
    data_cells = data_rows * cols if cols > 0 else 0
    
    print(f"\n📐 Table Dimensions:")
    print(f"   • Size: {rows} rows × {cols} columns")
    print(f"   • Total Cells: {total_cells}")
    print(f"   • Data Cells: {data_cells} (excluding header)")
    
    # Fill analysis (excluding ALL headers)
    fill_pct, fill_details = calculate_fill_percentage(analysis)
    empty_cells = fill_details['total'] - fill_details['filled']
    
    print(f"\n📊 Content Analysis (Data Cells Only - Excluding Headers):")
    print(f"   • Fill Percentage: {fill_details['percentage']}%")
    print(f"   • Filled Data Cells: {fill_details['filled']}/{fill_details['total']}")
    print(f"   • Empty Data Cells: {empty_cells}/{fill_details['total']}")
    
    # Word count
    meaningful_words = analysis.get('meaningful_words', 0)
    total_words = analysis.get('words', 0)
    dates = analysis.get('dates', 0)
    has_priority, priority_reason, priority_counts = check_priority_content(analysis)
    
    print(f"\n📝 Word & Content Metrics:")
    print(f"   • Meaningful Words: {meaningful_words} (includes {dates} dates)")
    print(f"   • Total Words: {total_words}")
    print(f"   • Links: {priority_counts['links']}")
    print(f"   • Images: {priority_counts['images']}")
    print(f"   • Files: {priority_counts['files']}")
    print(f"   • Mentions: {priority_counts['mentions']}")
    print(f"   • Dates: {dates}")
    
    # Row-wise summary
    per_row = analysis.get('per_row_summaries', [])
    
    print(f"\n📋 Row-wise Summary:")
    for row_idx, row_summary in enumerate(per_row):
        row_type = "HEADER" if row_idx == 0 else f"Row {row_idx}"
        row_meaningful = row_summary.get('meaningful_words', 0)
        row_total = row_summary.get('word_count', 0)
        row_total_cells = row_summary.get('cols', 0)
        row_empty_cells = row_summary.get('empty_cell_count', 0)
        row_filled_cells = row_total_cells - row_empty_cells
        
        print(f"   {row_type}: {row_filled_cells}/{row_total_cells} cells | {row_meaningful} meaningful words")


def print_analysis_medium_large(analysis: Dict[str, Any], decision: str, decision_info: Dict, table_idx: int, size_category: str):
    """Print analysis for medium and large tables (current detailed logic)."""
    
    # Header
    if decision == "USEFUL":
        emoji = "✅"
    elif decision == "GIBBERISH":
        emoji = "❌"
    else:
        emoji = "⚠️ "
    
    size_label = "MEDIUM Table" if size_category == "MEDIUM" else "LARGE Table"
    fill_info = decision_info.get('fill_info', 'N/A')
    
    print(f"\n{'─'*80}")
    print(f"🔷 Table {table_idx + 1}: {emoji} {decision} [{size_label}]")
    print(f"   Reason: {decision_info['reason']}")
    print(f"   Fill: {fill_info}")
    print(f"{'─'*80}")
    
    # 1. Table Dimensions
    rows = analysis.get('rows', 0)
    cols = analysis.get('cols', 0)
    total_cells = rows * cols
    data_rows = rows - 1 if rows > 1 else 0
    data_cells = data_rows * cols if cols > 0 else 0
    
    print(f"\n📐 Table Dimensions:")
    print(f"   • Size: {rows} rows × {cols} columns")
    print(f"   • Total Cells: {total_cells}")
    print(f"   • Data Rows: {data_rows} (excluding header)")
    print(f"   • Data Cells: {data_cells} (excluding header)")
    
    # 2. Direct Metrics
    has_priority, priority_reason, priority_counts = check_priority_content(analysis)
    meaningful_words = analysis.get('meaningful_words', 0)
    total_words = analysis.get('words', 0)
    
    dates = analysis.get('dates', 0)
    
    print(f"\n📊 Content Metrics:")
    print(f"   • Links: {priority_counts['links']}")
    print(f"   • Images: {priority_counts['images']}")
    print(f"   • File References: {priority_counts['files']}")
    print(f"   • User Mentions: {priority_counts['mentions']}")
    print(f"   • Dates: {dates}")
    print(f"   • Meaningful Words: {meaningful_words} (includes {dates} dates)")
    print(f"   • Total Words: {total_words}")
    
    # 3. Fill Percentage (excluding ALL headers)
    fill_pct, fill_details = calculate_fill_percentage(analysis)
    empty_cells = fill_details['total'] - fill_details['filled']
    
    print(f"\n📈 Fill Analysis (Data Cells Only - Excluding All Headers):")
    print(f"   • Fill Percentage: {fill_details['percentage']}%")
    print(f"   • Filled Data Cells: {fill_details['filled']}/{fill_details['total']}")
    print(f"   • Empty Data Cells: {empty_cells}/{fill_details['total']}")
    
    # 4. Structural Boolean Checks
    first_row_only, first_row_reason = check_first_row_only_filled(analysis)
    first_col_only, first_col_reason = check_first_column_only_filled(analysis)
    single_filled, single_reason, single_details = check_single_row_or_column_filled(analysis)
    
    print(f"\n🔍 Structural Checks:")
    print(f"   • Is Only 1st Row Filled: {first_row_only}")
    print(f"   • Is Only 1st Column Filled: {first_col_only}")
    
    # Check if any single row or column is filled
    only_one_row_filled = single_filled and single_details.get('filled_rows', 0) == 1
    only_one_col_filled = single_filled and single_details.get('filled_cols', 0) == 1
    
    print(f"   • Only 1 Row Filled (anywhere): {only_one_row_filled}")
    print(f"   • Only 1 Column Filled (anywhere): {only_one_col_filled}")
    
    # 5. Empty rows/columns count
    empty_counts = count_empty_rows_and_columns(analysis)
    
    print(f"\n🗑️  Empty Rows/Columns (Excluding Headers):")
    print(f"   • Empty Rows: {empty_counts['empty_rows']}/{empty_counts['total_data_rows']}")
    print(f"   • Empty Columns: {empty_counts['empty_cols']}/{empty_counts['total_cols']}")
    
    # 6. Placeholder words
    placeholder_words = analysis.get('placeholder_words', 0)
    
    print(f"\n⚠️  Placeholder Content:")
    print(f"   • Placeholder Words: {placeholder_words}")
    
    # 7. Header Analysis - Check if header contains most content
    per_row = analysis.get('per_row_summaries', [])
    
    if per_row:
        header_words = per_row[0].get('meaningful_words', 0) if len(per_row) > 0 else 0
        data_words = sum(row.get('meaningful_words', 0) for row in per_row[1:])
        total_meaningful = meaningful_words
        
        if total_meaningful > 0:
            header_percentage = (header_words / total_meaningful * 100) if total_meaningful > 0 else 0
            
            print(f"\n📋 Header Analysis:")
            print(f"   • Header Words: {header_words} meaningful ({header_percentage:.1f}% of total)")
            print(f"   • Data Rows Words: {data_words} meaningful ({100-header_percentage:.1f}% of total)")
            
            # Warn if header has majority of content
            if header_percentage > 70 and data_rows > 0:
                print(f"   ⚠️  WARNING: Header contains {header_percentage:.1f}% of content!")
                print(f"   ⚠️  This suggests 'heading in column only' pattern - may be gibberish")
    
    # 8. Content Row-wise
    print(f"\n📋 Content Row-wise:")
    for row_idx, row_summary in enumerate(per_row):
        row_type = "HEADER" if row_idx == 0 else f"Row {row_idx}"
        row_meaningful = row_summary.get('meaningful_words', 0)
        row_total = row_summary.get('word_count', 0)
        row_links = row_summary.get('links', 0)
        row_files = row_summary.get('files', 0)
        row_images = row_summary.get('images', 0)
        row_mentions = row_summary.get('mentions', 0)
        row_placeholder = row_summary.get('placeholder_words', 0)
        row_dates = row_summary.get('dates', 0)
        
        # Calculate cell fill information
        row_total_cells = row_summary.get('cols', 0)
        row_empty_cells = row_summary.get('empty_cell_count', 0)
        row_filled_cells = row_total_cells - row_empty_cells
        
        print(f"   {row_type}:")
        print(f"      Cells: {row_filled_cells}/{row_total_cells} filled | "
              f"Words: {row_meaningful} meaningful / {row_total} total | "
              f"Links: {row_links} | Files: {row_files} | Images: {row_images} | "
              f"Mentions: {row_mentions} | Dates: {row_dates} | Placeholders: {row_placeholder}")


def print_analysis(analysis: Dict[str, Any], decision: str, decision_info: Dict, table_idx: int):
    """
    Route to appropriate analysis function based on table size.
    
    This is the main entry point that delegates to size-specific analysis functions.
    """
    # Categorize table by size
    size_category = categorize_table_size(analysis)
    
    # Route to appropriate analysis function
    if size_category == "VERY_SMALL":
        print_analysis_very_small(analysis, decision, decision_info, table_idx)
    elif size_category == "SMALL":
        print_analysis_small(analysis, decision, decision_info, table_idx)
    else:  # MEDIUM or LARGE
        print_analysis_medium_large(analysis, decision, decision_info, table_idx, size_category)


def decide_page_quality(table_decisions: List[str]) -> str:
    """Aggregate table decisions to page level."""
    if not table_decisions:
        return "GIBBERISH"
    
    useful_count = table_decisions.count("USEFUL")
    gibberish_count = table_decisions.count("GIBBERISH")
    
    total = len(table_decisions)
    
    if useful_count >= total * 0.5:
        return "USEFUL"
    if gibberish_count >= total * 0.5:
        return "GIBBERISH"
    
    return "CAN'T DECIDE"


# =============================================================================
#                           MAIN EXECUTION
# =============================================================================

def main():
    """Main execution - analyzes document at DEFAULT_TEST_INDEX."""
    # Import here to avoid circular dependency
    from filter.main.collect import collect_document_data
    
    index = DEFAULT_TEST_INDEX
    dump_file_name = DATA_FILE
    
    with open(dump_file_name, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f):
            if line_number != index:
                continue
            
            data = json.loads(line)
            doc_id = data.get("id")
            doc_data = collect_document_data(data)
            
            # Header
            print("\n" + "="*80)
            print("📄 TABLE QUALITY ANALYSIS - Priority-Based Decision System")
            print("="*80)
            print(f"URL: {doc_data['url']}")
            print(f"Title: {doc_data['title']}")
            print(f"ID: {doc_id}")
            
            tables = doc_data.get('tables', [])
            if not tables:
                print(f"\n⚠️  No tables found in document")
                print("="*80 + "\n")
                return
            
            print(f"\n📊 Document contains {len(tables)} table(s)")
            
            # Analyze each table
            table_decisions = []
            
            for table in tables:
                table_index = table.get('table_index')
                analysis = table.get('analysis', {})
                
                # Make decision
                decision, decision_info = decide_table_quality(analysis)
                table_decisions.append(decision)
                
                # Print analysis
                print_analysis(analysis, decision, decision_info, table_index)
            
            # Overall decision
            page_decision = decide_page_quality(table_decisions)
            print("\n" + "="*80)
            
            if page_decision == "USEFUL":
                emoji = "✅"
            elif page_decision == "GIBBERISH":
                emoji = "❌"
            else:
                emoji = "⚠️ "
            
            print(f"📊 Overall Page Decision: {emoji} {page_decision}")
            cant_decide_count = table_decisions.count("CAN'T DECIDE")
            print(f"   Useful: {table_decisions.count('USEFUL')} | "
                  f"Gibberish: {table_decisions.count('GIBBERISH')} | "
                  f"Can't Decide: {cant_decide_count}")
            print("="*80 + "\n")
            
            break


if __name__ == "__main__":
    main()
