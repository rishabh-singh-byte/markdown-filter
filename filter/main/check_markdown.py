"""
Confluence Page Analyzer
=========================
Analyzes Confluence pages using HTML 'body' field.
Converts HTML to Markdown and performs structural analysis with robust table handling.

This script uses conversion3.py for HTML to Markdown conversion.
"""

# =============================================================================
#                           IMPORTS
# =============================================================================

import json
import re
import sys
import os
import html
from typing import List, Dict, Any, Tuple, Optional

# Add current directory to path to import conversion3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
#                           CONFIGURATION PARAMETERS
# =============================================================================

DEFAULT_DATA_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/data/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 100

# =============================================================================
#                           CONVERSION MODULE IMPORT
# =============================================================================

# Import conversion3 module for HTML to Markdown conversion
CONVERSION3_AVAILABLE = False
convert_html_to_markdown_func: Optional[callable] = None

try:
    from conversion3 import convert_html_to_markdown as conversion3_converter
    convert_html_to_markdown_func = conversion3_converter
    CONVERSION3_AVAILABLE = True
    print("✅ Using conversion3.py for HTML to Markdown conversion")
except ImportError as e:
    print(f"⚠️ conversion3.py not available: {e}")
    print("🔄 Falling back to basic HTML to Markdown conversion")
    CONVERSION3_AVAILABLE = False

# =============================================================================
#                           UTILITY HELPER FUNCTIONS
# =============================================================================

def count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(re.findall(r"\b[\w'-]+\b", text))

def count_links(text: str) -> int:
    """Count links in text."""
    if not text:
        return 0
    return len(re.findall(r"https?://[^\s)]+", text))

def count_words_per_paragraph(text: str) -> int:
    """Count words per paragraph in text."""
    if not text:
        return 0
    return len([p for p in re.split(r"\n\s*\n", text) if p.strip()])

def contains_url(text: str) -> bool:
    """Check if text contains URL."""
    if not text:
        return False
    return bool(re.search(r"https?://[^\s)]+", text))


def contains_image_reference(text: str) -> bool:
    """Check if text contains image reference."""
    if not text:
        return False
    return bool(re.search(r"\b\S+\.(png|jpg|jpeg|gif|svg|bmp|webp)\b", text, re.I))


def count_mentions(table: List[List[str]], label: str) -> Tuple[int, List[str]]:
    """
    Find the row whose first cell matches the given label (case-insensitive)
    and count all user mentions [~XXXXXXXX] in the corresponding cell(s).
    """
    label = label.strip().lower()

    for row in table:
        if not row:
            continue
        first_cell = row[0].strip().lower()
        if label == first_cell or label in first_cell:
            # Combine all other cells (sometimes data can be spread across multiple columns)
            content = " ".join(row[1:])
            mentions = re.findall(r"\[~[^\]]+\]", content)
            return len(mentions), mentions

    return 0, []


def count_mentions_in_text(text: str) -> Tuple[int, List[str]]:
    """
    Count all user mentions [~XXXXXXXX] in the given text.
    Returns tuple of (count, list of mentions).
    """
    if not text:
        return 0, []
    mentions = re.findall(r"\[~[^\]]+\]", text)
    return len(mentions), mentions


def contains_filename_like(text: str) -> bool:
    """Check if text contains file reference."""
    if not text:
        return False
    return bool(re.search(r"\b\S+\.(pdf|docx?|xlsx?|csv|pptx?)\b", text, re.I))


# =============================================================================
#                       HTML TO MARKDOWN - DELEGATED TO CONVERSION3
# =============================================================================
# All HTML to Markdown conversion is handled by conversion3.py
# This section is intentionally minimal to keep the code clean and maintainable


def html_to_markdown(html_str: str) -> str:
    """
    Converts raw Confluence HTML content to Markdown format using conversion3.py.
    
    This function delegates all HTML to Markdown conversion to conversion3.py, which handles:
    - Confluence macros (code, toc, expand, status, jira, task-list, etc.)
    - Tables with proper header detection and nested table support
    - Lists (ordered and unordered, with nesting)
    - Images and links (including Confluence attachments)
    - User mentions (ac:link with ri:user tags)
    - Code blocks with syntax highlighting
    - Emoticons and special Confluence elements
    
    Args:
        html_str: Raw Confluence HTML/XHTML content (storage format)
        
    Returns:
        Markdown-formatted string
        
    Raises:
        RuntimeError: If conversion3.py is not available
    """
    if not html_str or not html_str.strip():
        return ""
    
    # Ensure conversion3.py is available
    if not CONVERSION3_AVAILABLE or not convert_html_to_markdown_func:
        error_msg = (
            "❌ conversion3.py is required but not available.\n"
            "   Please ensure conversion3.py is in the same directory as check_markdown.py"
        )
        raise RuntimeError(error_msg)
    
    # Delegate conversion to conversion3.py
    try:
        markdown_result = convert_html_to_markdown_func(html_str)
        return markdown_result
    except Exception as e:
        print(f"❌ conversion3.py failed with error: {e}")
        raise


# =============================================================================
#                       MARKDOWN TABLE EXTRACTION
# =============================================================================

def extract_tables_from_markdown(md: str) -> List[List[List[str]]]:
    """
    Extracts all tables from markdown text as a list of tables.
    Each table is a list of rows, each row is a list of cell strings.
    Handles standard and non-standard markdown tables.
    """
    if not md:
        return []

    lines = [line.rstrip() for line in md.splitlines()]
    tables = []
    current_block = []

    # check if the line is a separator row
    def is_separator_row(s: str) -> bool:
        """Check if line is a table separator row (e.g., | --- | --- |)"""
        s = s.strip().strip('|')
        parts = [p.strip() for p in s.split('|')]
        # All parts should be dashes/colons only
        return all(re.fullmatch(r'[-:\s]+', p) for p in parts if p)

    # flush the block when the table is complete, if the block has at least 2 lines
    def flush_block():
        nonlocal current_block
        if len(current_block) >= 2:
            # Check for proper table with separator row
            has_separator = any(is_separator_row(l) for l in current_block)
            if has_separator:
                # Filter out separator rows and parse cells
                table_lines = [l for l in current_block if l.strip() and not is_separator_row(l)]
                table = [parse_cells(l) for l in table_lines if "|" in l]
                if table:
                    tables.append(table)
        current_block = []

    def is_table_line(s: str) -> bool:
        """Check if line is part of a table"""
        if not s.strip() or '|' not in s:
            return False
        # Must start with pipe or have content-pipe-content pattern
        stripped = s.strip()
        if not (stripped.startswith('|') or '|' in stripped):
            return False
        # Split and check for multiple cells
        parts = [p.strip() for p in stripped.strip('|').split('|')]
        return len(parts) > 1

    def parse_cells(s: str) -> List[str]:
        """Parse cells from table row, handling escaped pipes"""
        s = s.strip().strip('|')
        cells = []
        current_cell = ""
        escaped = False
        
        for char in s:
            if char == '\\' and not escaped:
                escaped = True
                continue
            if char == '|' and not escaped:
                cells.append(current_cell.strip())
                current_cell = ""
            else:
                if escaped and char == '|':
                    current_cell += '|'
                else:
                    current_cell += char
                escaped = False
        
        if current_cell or s.endswith('|'):
            cells.append(current_cell.strip())
        
        return cells

    for line in lines:
        if is_table_line(line):
            current_block.append(line)
        else:
            flush_block()

    flush_block()  # flush last one
    return tables


# =============================================================================
#                       TABLE CONTENT ANALYSIS
# =============================================================================

# def _count_contiguous_empty_blocks(row: List[str]) -> List[int]:
#     """Count contiguous empty cell blocks in a row."""
#     blocks, current = [], 0
#     for c in row:
#         if not c.strip():
#             current += 1
#         elif current:
#             blocks.append(current)
#             current = 0
#     if current:
#         blocks.append(current)
#     return blocks


def find_contiguous_empty_blocks(row_empty_flags: List[bool]) -> List[Dict[str, int]]:
    """
    Finds contiguous blocks of empty cells in a row.
    Returns list of dicts with start and end indices.
    """
    blocks = []
    start = None
    for i, flag in enumerate(row_empty_flags):
        if flag and start is None:
            start = i
        if not flag and start is not None:
            blocks.append({"start": start, "end": i - 1})
            start = None
    if start is not None:
        blocks.append({"start": start, "end": len(row_empty_flags) - 1})
    return blocks

def detect_table_heading(table: List[List[str]]) -> Dict[str, Any]:
    """
    Detect table headers based purely on bold markdown syntax (**xyz**).
    Rules:
      - The *entire* first row must be bold to count as column headers.
      - The *entire* first column must be bold to count as row headers.
      - If both are bold, (0,0) cell is ignored for row headers.
    Returns:
      {
        "column_headers": list or None,
        "row_headers": list or None,
        "heading_type": "row" | "column" | "both" | "none"
      }
    """

    if not table or not any(table):
        return {
            "column_headers": None,
            "row_headers": None,
            "heading_type": "none"
        }

    rows = len(table)
    cols = max((len(r) for r in table), default=0)
    
    if rows == 0 or cols == 0:
        return {
            "column_headers": None,
            "row_headers": None,
            "heading_type": "none"
        }
    
    # Normalize all rows to same length
    norm_table = [r + [""] * (cols - len(r)) for r in table]

    bold_pattern = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")

    def is_bold_cell(cell: str) -> bool:
        """Check if cell content is bold"""
        if not cell or not cell.strip():
            return False
        return bool(bold_pattern.match(cell.strip()))

    def extract_bold_text(cell: str) -> str:
        """Extract text from bold cell"""
        if not cell or not cell.strip():
            return ""
        match = bold_pattern.match(cell.strip())
        return match.group(1).strip() if match else cell.strip()

    # --- Check if all non-empty cells in first row are bold ---
    first_row = norm_table[0]
    non_empty_first_row = [c for c in first_row if c.strip()]
    all_first_row_bold = len(non_empty_first_row) > 0 and all(is_bold_cell(c) for c in non_empty_first_row)

    # --- Check if all non-empty cells in first column are bold ---
    first_col = [r[0] for r in norm_table if r]
    non_empty_first_col = [c for c in first_col if c.strip()]
    all_first_col_bold = len(non_empty_first_col) > 0 and all(is_bold_cell(c) for c in non_empty_first_col)

    # --- SPECIAL CASE: 2-column key-value table ---
    # If table has exactly 2 columns and first column has content but second is mostly empty,
    # treat first column as row headers even if not bold
    is_key_value_table = False
    if cols == 2 and not all_first_col_bold and not all_first_row_bold:
        # Check if first column has content and second column is mostly empty
        second_col = [r[1] if len(r) > 1 else "" for r in norm_table]
        first_col_filled = sum(1 for c in first_col if c.strip())
        second_col_filled = sum(1 for c in second_col if c.strip())
        
        # If first column is mostly filled and second column is mostly empty, it's key-value
        if first_col_filled >= rows * 0.5 and second_col_filled <= rows * 0.5:
            is_key_value_table = True

    # --- Extract column headers (if full first row is bold) ---
    if all_first_row_bold:
        column_headers = [extract_bold_text(c) for c in first_row]
    else:
        column_headers = None

    # --- Extract row headers (if full first column is bold OR if it's a key-value table) ---
    if all_first_col_bold or is_key_value_table:
        # Skip index [0][0] if both headers exist
        start_row = 1 if all_first_row_bold else 0
        row_headers = [
            extract_bold_text(norm_table[r][0]) if all_first_col_bold else norm_table[r][0].strip()
            for r in range(start_row, rows)
        ]
    else:
        row_headers = None

    # --- HEURISTIC: Detect non-bold column headers ---
    # If first row not detected as bold headers, check if it looks like headers:
    # - All cells are short (field names)
    # - Not example/placeholder data
    if not column_headers and rows >= 1:
        first_row_looks_like_headers = True
        non_empty_cells = 0
        
        for cell in first_row:
            cell_stripped = cell.strip()
            if not cell_stripped:  # Empty cells in header are okay
                continue
            
            non_empty_cells += 1
            
            # Check if cell looks like a field name (short, no placeholders, capitalized words)
            word_count = len(re.findall(r'\b\w+\b', cell_stripped))
            # Headers typically have 1-3 words (e.g., "User Story", "Date", "Notes")
            if word_count > 4:
                first_row_looks_like_headers = False
                break
            # If it starts with "e.g." it's example data, not a header
            if cell_stripped.lower().startswith('e.g.'):
                first_row_looks_like_headers = False
                break
        
        # Need at least 2 non-empty cells to be a valid header row
        # If first row looks like headers, treat it as column headers
        if first_row_looks_like_headers and non_empty_cells >= 2:
            column_headers = [c.strip() for c in first_row]

    # --- Determine heading type ---
    if column_headers and row_headers:
        heading_type = "both"
    elif column_headers:
        heading_type = "column"
    elif row_headers:
        heading_type = "row"
    else:
        heading_type = "none"

    return {
        "column_headers": column_headers,
        "row_headers": row_headers,
        "heading_type": heading_type,
        "is_key_value_table": is_key_value_table
    }



def cell_metrics(cell_text: str) -> Dict[str, Any]:
    """
    Analyze a single cell text for emptiness, words, links, images, files, and mentions.
    Classifies words into meaningful vs placeholder/index categories.
    """
    # Define placeholder words that don't contribute meaningful content
    PLACEHOLDER_WORDS = {
        'draft', 'tbd', 'yes', 'no', 'none', 'n/a', 'na', 'todo', 'pending',
        'ok', 'done', 'wip', 'placeholder', 'example', 'sample', 'test',
        'tmp', 'temp', 'xxx', 'yyy', 'zzz', 'abc', 'tba', 'high', 'low', 'medium', 
        'medium-high', 'medium-low', 'high-medium', 'low-medium', 'high-low', 'low-high',
        'status',  # Status indicators like [STATUS: DRAFT]
    }
    
    def is_index_pattern(word: str) -> bool:
        """
        Check if a word is an index/counter (numeric, roman numeral, or alphabetic).
        Returns True for: 1, 2, 100, i, ii, iii, iv, v, x, a, b, c, aa, bb, etc.
        """
        word_clean = word.strip().lower()
        
        # Pure numeric (1, 2, 10, 100, etc.)
        if word_clean.isdigit():
            return True
        
        # Roman numerals (i, ii, iii, iv, v, vi, vii, viii, ix, x, xi, xii, etc.)
        # Common pattern: only contains i, v, x, l, c, d, m
        if word_clean and all(c in 'ivxlcdm' for c in word_clean):
            # Additional check: valid roman numeral patterns
            if re.fullmatch(r'^m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$', word_clean):
                return True
        
        # Single alphabetic character (a, b, c, ..., z)
        if len(word_clean) == 1 and word_clean.isalpha():
            return True
        
        # Repeated alphabetic character (aa, bb, cc, etc.)
        if len(word_clean) <= 3 and word_clean and all(c == word_clean[0] for c in word_clean) and word_clean[0].isalpha():
            return True
        
        return False
    
    text = cell_text or ""
    stripped = text.strip()
    is_empty = (len(stripped) == 0)

    # Extract all words
    all_words = re.findall(r'\b\w+\b', text) if not is_empty else []
    total_words = len(all_words)
    
    # Classify words as meaningful, placeholder, or index
    placeholder_words = []
    meaningful_words = []
    index_words = []
    
    for word in all_words:
        word_lower = word.lower()
        # Remove markdown bold/italic markers
        clean_word = word_lower.strip('*_')
        
        # Check if it's an index pattern first
        if is_index_pattern(word):
            index_words.append(word)
        elif clean_word in PLACEHOLDER_WORDS:
            placeholder_words.append(word)
        else:
            meaningful_words.append(word)
    
    meaningful_word_count = len(meaningful_words)
    placeholder_word_count = len(placeholder_words) + len(index_words)  # Count indices as placeholders
    
    # Extract other metrics
    links = len(re.findall(r"https?://[^\s)]+", text))
    images = len(re.findall(r"\b\S+\.(png|jpg|jpeg|gif|svg|bmp|webp)\b", text, re.I))
    files = len(re.findall(r"\b\S+\.(pdf|docx?|xlsx?|csv|pptx?)\b", text, re.I))
    mention_count, mentions = count_mentions_in_text(text)

    return {
        "text": text,
        "words": total_words,
        "meaningful_words": meaningful_word_count,
        "placeholder_words": placeholder_word_count,
        "meaningful_word_list": meaningful_words,
        "placeholder_word_list": placeholder_words,
        "index_word_list": index_words,
        "links": links,
        "images": images,
        "files": files,
        "mentions": mention_count,
        "mention_list": mentions,
        "empty": is_empty,
        "has_useful_content": meaningful_word_count >= 2 or links > 0 or images > 0 or files > 0 or mention_count > 0
    }


def analyze_table_content(table: List[List[str]], label_col_count: int = 1) -> Dict[str, Any]:
    """
    Analyzes the table content and returns comprehensive statistics.
    Word counts EXCLUDE heading cells and distinguish meaningful vs placeholder words.
    
    Args:
        table: List of rows, each row is a list of cell strings
        label_col_count: number of initial columns to treat as labels (not data)
    
    Returns:
        Dictionary with detailed table analysis including:
        - words: total word count (excluding headings)
        - meaningful_words: words excluding placeholders (excluding headings)
        - placeholder_words: placeholder word count (excluding headings)
    """
    if not table:
        return {
            "rows": 0,
            "cols": 0,
            "total_cells": 0,
            "filled_cells": 0,
            "fill_percentage": 0.0,
            "words": 0,
            "meaningful_words": 0,
            "placeholder_words": 0,
            "links": 0,
            "images": 0,
            "files": 0,
            "mentions": 0,
            "empty_cell_count": 0,
            "empty_cell_coords": [],
            "empty_rows": [],
            "empty_columns": [],
            "per_row_summaries": [],
            "cell_metrics_grid": [],
            "is_empty_table": True,
            "is_useful_table": False,
            "headings": None,
        }

    rows = len(table)
    cols = max(len(r) for r in table)

    # Normalize row lengths
    norm_table = [row + [""] * (cols - len(row)) for row in table]

    # Detect headers first to exclude them from word count
    headings = detect_table_heading(table)
    heading_type = headings.get("heading_type", "none")
    
    # Determine which cells are headers
    has_column_headers = heading_type in ["column", "both"]
    has_row_headers = heading_type in ["row", "both"]

    total_cells = rows * cols
    filled_cells = 0
    
    # Word counts (excluding headings)
    total_words = 0
    meaningful_words_count = 0
    placeholder_words_count = 0
    
    # Other metrics
    total_links = 0
    total_images = 0
    total_files = 0
    total_mentions = 0

    empty_cell_coords = []
    per_col_empty_counts = [0] * cols
    per_row_summaries = []
    cell_metrics_grid = []
    
    # Track if table has any useful content
    has_any_useful_content = False

    for r_idx, row in enumerate(norm_table):
        row_metrics = []
        row_word_sum = 0
        row_meaningful_words = 0
        row_placeholder_words = 0
        row_links = 0
        row_images = 0
        row_files = 0
        row_mentions = 0
        row_empty_flags = []

        for c_idx, cell in enumerate(row):
            cm = cell_metrics(cell)
            row_metrics.append(cm)

            # Determine if this cell is a header cell
            is_header_cell = False
            if has_column_headers and r_idx == 0:
                # First row is column header
                is_header_cell = True
            if has_row_headers and c_idx == 0:
                # First column is row header
                is_header_cell = True

            # Count words only for non-header cells (data cells)
            if not is_header_cell:
                total_words += cm["words"]
                meaningful_words_count += cm["meaningful_words"]
                placeholder_words_count += cm["placeholder_words"]
                row_word_sum += cm["words"]
                row_meaningful_words += cm["meaningful_words"]
                row_placeholder_words += cm["placeholder_words"]
                
                # Check if this cell has useful content
                if cm["has_useful_content"]:
                    has_any_useful_content = True
            
            # Count other metrics for all cells (including headers for completeness)
            total_links += cm["links"]
            total_images += cm["images"]
            total_files += cm["files"]
            total_mentions += cm["mentions"]

            if cm["empty"]:
                empty_cell_coords.append((r_idx, c_idx))
                per_col_empty_counts[c_idx] += 1
                row_empty_flags.append(True)
            else:
                filled_cells += 1
                row_empty_flags.append(False)

            row_links += cm["links"]
            row_images += cm["images"]
            row_files += cm["files"]
            row_mentions += cm["mentions"]

        empty_blocks = find_contiguous_empty_blocks(row_empty_flags)

        per_row_summaries.append({
            "row_index": r_idx,
            "cols": len(row),
            "word_count": row_word_sum,
            "meaningful_words": row_meaningful_words,
            "placeholder_words": row_placeholder_words,
            "links": row_links,
            "images": row_images,
            "files": row_files,
            "mentions": row_mentions,
            "empty_cell_count": sum(row_empty_flags),
            "empty_blocks": empty_blocks,
            "cell_metrics": row_metrics
        })

        cell_metrics_grid.append(row_metrics)

    empty_columns = [i for i, cnt in enumerate(per_col_empty_counts) if cnt == rows]
    empty_rows = [r["row_index"] for r in per_row_summaries if r["empty_cell_count"] == cols]

    fill_percentage = round((filled_cells / total_cells) * 100, 2) if total_cells > 0 else 0.0

    # Determine if table is empty based on label columns skipped
    # Table is empty if *all* data cells (columns after label columns) are empty
    data_cells = []
    for r in norm_table:
        data_cells.extend(r[label_col_count:])  # skip label columns

    # Check if all data cells empty (only whitespace or empty)
    is_empty_table = all(cell_metrics(cell)["empty"] for cell in data_cells)

    return {
        "rows": rows,
        "cols": cols,
        "total_cells": total_cells,
        "filled_cells": filled_cells,
        "fill_percentage": fill_percentage,
        "words": total_words,
        "meaningful_words": meaningful_words_count,
        "placeholder_words": placeholder_words_count,
        "links": total_links,
        "images": total_images,
        "files": total_files,
        "mentions": total_mentions,
        "empty_cell_count": len(empty_cell_coords),
        "empty_cell_coords": empty_cell_coords,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "per_row_summaries": per_row_summaries,
        "cell_metrics_grid": cell_metrics_grid,
        "is_empty_table": is_empty_table,
        "is_useful_table": has_any_useful_content,
        "headings": headings,
    }


# =============================================================================
#                       MARKDOWN STRUCTURE ANALYSIS
# =============================================================================

def find_links_images(text: str) -> Dict[str, int]:
    """Find and count links, images, file references, and mentions in text."""
    if not text:
        return {"links": 0, "images": 0, "file_refs": 0, "mentions": 0}
    
    mention_count, _ = count_mentions_in_text(text)
    
    return {
        "links": len(re.findall(r"https?://[^\s)]+", text)),
        "images": len(re.findall(r"\b\S+\.(png|jpg|jpeg|gif|svg|bmp|webp)\b", text, re.I)),
        "file_refs": len(re.findall(r"\b\S+\.(pdf|docx?|xlsx?|csv|pptx?)\b", text, re.I)),
        "mentions": mention_count,
    }


def analyze_markdown_structure(md: str) -> Dict[str, Any]:
    """
    Analyzes the overall markdown structure (headings, paragraphs, lists, etc.)
    Word count EXCLUDES heading text.
    """
    if not md:
        return {
            "word_count": 0,
            "word_count_with_headings": 0,
            "heading_word_count": 0,
            "paragraphs": 0,
            "total_headings": 0,
            "main_headings": 0,
            "subheadings": 0,
            "headings_breakdown": {},
            "unordered_items": 0,
            "ordered_items": 0,
            "code_blocks": 0,
            "blockquotes": 0,
            "images_count": 0,
        }

    paragraphs = len([p for p in re.split(r"\n\s*\n", md) if p.strip()])
    headings = re.findall(r"^(#{1,6})\s+(.+)", md, flags=re.M)

    heading_count = {}
    heading_word_count = 0
    
    for hashes, heading_text in headings:
        level = f"h{len(hashes)}"
        heading_count[level] = heading_count.get(level, 0) + 1
        
        # Count words in this heading (excluding markdown syntax)
        # Remove bold/italic markers and other markdown from heading text
        clean_heading = re.sub(r'[*_`\[\]()]', '', heading_text)
        heading_words = len(re.findall(r'\b\w+\b', clean_heading))
        heading_word_count += heading_words

    # Count total words in markdown, but first remove metadata content and tables
    md_for_counting = md
    
    # Remove tables entirely (including headers, separators, and data)
    # Tables are lines starting with '|'
    md_for_counting = re.sub(r'^[|\s]*\|.*$', '', md_for_counting, flags=re.M)
    
    # Remove blockquotes (UI instructions, info boxes, etc.)
    md_for_counting = re.sub(r'^>.*$', '', md_for_counting, flags=re.M)
    
    # Remove macros (e.g., [MACRO: Roadmap Planner ...])
    md_for_counting = re.sub(r'\[MACRO:.*?\]', '', md_for_counting)
    
    # Remove summary tags content (but keep details block content like tables)
    md_for_counting = re.sub(r'<summary>.*?</summary>', '', md_for_counting, flags=re.DOTALL)
    
    # Remove details opening/closing tags (but keep content between them)
    md_for_counting = re.sub(r'<details>', '', md_for_counting)
    md_for_counting = re.sub(r'</details>', '', md_for_counting)
    
    # Remove image alt text and URLs
    md_for_counting = re.sub(r'!\[.*?\]\(.*?\)', '', md_for_counting)
    
    # Count total words
    total_word_count = len(re.findall(r'\b\w+\b', md_for_counting))
    
    # Word count excluding headings
    word_count_excluding_headings = total_word_count - heading_word_count

    return {
        "word_count": word_count_excluding_headings,
        "word_count_with_headings": total_word_count,
        "heading_word_count": heading_word_count,
        "paragraphs": paragraphs,
        "total_headings": sum(heading_count.values()),
        "main_headings": heading_count.get("h1", 0),
        "subheadings": sum(v for k, v in heading_count.items() if k != "h1"),
        "headings_breakdown": heading_count,
        "unordered_items": len(re.findall(r"^\s*[-*+]\s+", md, flags=re.M)),
        "ordered_items": len(re.findall(r"^\s*\d+\.\s+", md, flags=re.M)),
        "code_blocks": len(re.findall(r"```", md)) // 2,
        "blockquotes": len(re.findall(r"^>\s+", md, flags=re.M)),
        "images_count": len(re.findall(r"!\[.*?\]\((.*?)\)", md)),
    }


# =============================================================================
#                           DOCUMENT SUMMARY
# =============================================================================

def summarize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate comprehensive document summary with table analysis.
    
    Args:
        doc: Document dictionary with 'body', 'id', 'title', 'url' fields
    
    Returns:
        Dictionary with complete document analysis
    """
    html_body = doc.get("body", "")
    md = html_to_markdown(html_body)

    tables = extract_tables_from_markdown(md)
    table_summaries = [analyze_table_content(t) for t in tables]
    text_scan = find_links_images(md)
    structure = analyze_markdown_structure(md)

    # Calculate word counts
    total_word_count = structure.get("word_count", 0)
    table_word_count = sum(t["words"] for t in table_summaries)
    word_count_excluding_tables = total_word_count - table_word_count

    return {
        "id": doc.get("id"),
        "title": doc.get("title"),
        "url": doc.get("url"),
        "num_tables": len(tables),
        "table_summaries": table_summaries,
        "table_images_count": sum(t["images"] for t in table_summaries),
        "table_mentions_count": sum(t["mentions"] for t in table_summaries),
        "table_word_count": table_word_count,
        "total_word_count": total_word_count,
        "word_count_excluding_tables": word_count_excluding_tables,
        "link_count": text_scan["links"],
        "image_count": text_scan["images"],
        "file_ref_count": text_scan["file_refs"],
        "mention_count": text_scan["mentions"],
        "structure_summary": structure,
    }


# =============================================================================
#                           REPORTING
# =============================================================================

def print_document_summary(summary: Dict[str, Any], index: int = 0):
    """Print formatted document summary to console."""
    print("\n" + "=" * 100)
    print(f"📄 Document [{index}] Summary")
    print("=" * 100)
    print(f"🔖 Title     : {summary.get('title', 'N/A')}")
    print(f"🆔 ID        : {summary.get('id', 'N/A')}")
    print(f"🌐 URL       : {summary.get('url', 'N/A')}")
    print("-" * 100)
    print("📊 Content Overview")
    print(f"  • Tables                        : {summary.get('num_tables', 0)}")
    print(f"  • Table Images                  : {summary.get('table_images_count', 0)}")
    print(f"  • Table Mentions                : {summary.get('table_mentions_count', 0)}")
    print(f"  • Links                         : {summary.get('link_count', 0)}")
    print(f"  • Images                        : {summary.get('image_count', 0)}")
    print(f"  • File References               : {summary.get('file_ref_count', 0)}")
    print(f"  • User Mentions                 : {summary.get('mention_count', 0)}")
    print(f"  • Total Word Count              : {summary.get('total_word_count', 0)} (excl. all headings)")
    print(f"  • Table Word Count              : {summary.get('table_word_count', 0)} (excl. table headings)")
    print(f"  • Word Count (Excluding Tables) : {summary.get('word_count_excluding_tables', 0)} (excl. headings)")
    print("-" * 100)
    print("📋 Table Summaries")

    if summary.get("table_summaries"):
        for i, t in enumerate(summary["table_summaries"], 1):
            print(f"\n  ▶ Table {i}:")
            print(f"     • Shape              : {t['rows']} rows × {t['cols']} cols")
            print(f"     • Fill %             : {t['fill_percentage']}% ({t['filled_cells']}/{t['total_cells']} cells filled)")
            print(f"     • Empty Rows         : {len(t['empty_rows'])}")
            print(f"     • Empty Columns      : {len(t['empty_columns'])}")
            print(f"     • Total Empty Cells  : {t['empty_cell_count']}")
            print(f"     • Total Words        : {t['words']} (excl. headings)")
            print(f"     • Meaningful Words   : {t.get('meaningful_words', 0)} (excl. placeholders & headings)")
            print(f"     • Placeholder Words  : {t.get('placeholder_words', 0)} (draft, tbd, yes, no, etc.)")
            print(f"     • Links              : {t['links']}")
            print(f"     • Images             : {t['images']}")
            print(f"     • File References    : {t['files']}")
            print(f"     • User Mentions      : {t['mentions']}")
            h = t.get("headings", {})
            print(f"     • Heading Type       : {h.get('heading_type')}")

            if h.get("column_headers"):
                print(f"     • Column Headers     : {h['column_headers']}")

            if h.get("row_headers"):
                print(f"     • Row Headers        : {h['row_headers']}")

            # Detect gibberish or sparse tables based on meaningful words
            is_useful = t.get("is_useful_table", False)
            meaningful = t.get('meaningful_words', 0)
            
            if t.get("is_empty_table", False):
                print(f"     • Notes              : ❌ Empty table")
            elif not is_useful or meaningful < 2:
                print(f"     • Notes              : ⚠️  Gibberish or placeholder table (no meaningful content)")
            elif t["fill_percentage"] < 30 and meaningful < 10:
                print(f"     • Notes              : ⚠️  Sparse table with limited content")
            else:
                print(f"     • Notes              : ✅ Useful table with meaningful content")

    else:
        print("  ❌ No tables found.")
    
    print("-" * 100)
    print("🧱 Structure Summary")
    structure = summary.get("structure_summary", {})
    for k, v in structure.items():
        print(f"  • {k:<20}: {v}")
    print("=" * 100 + "\n")


# =============================================================================
#                           MAIN EXECUTION
# =============================================================================

def process_json_obj(obj: Dict[str, Any], idx: int = 0):
    """
    Process a single JSON object from JSONL file.
    
    Args:
        obj: Document dictionary
        idx: Index of document in file
    
    Returns:
        Document summary dictionary
    """
    summary = summarize_document(obj)
    print_document_summary(summary, idx)
    return summary


if __name__ == "__main__":
    dump_file_name = DEFAULT_DATA_FILE

    try:
        with open(dump_file_name, "r", encoding="utf-8") as f:
            items = [json.loads(line) for line in f if line.strip()]
            if items:
                process_json_obj(items[DEFAULT_TEST_INDEX], idx=DEFAULT_TEST_INDEX)
            else:
                print("❌ No items found in the JSONL file")
    except FileNotFoundError:
        print(f"❌ File not found: {dump_file_name}")
    except Exception as e:
        print(f"❌ Error processing file: {e}")