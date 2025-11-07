"""
Label Studio Data Extractor - Confluence Format
================================================
Extracts Label Studio tasks with all confluence fields and
individual annotator responses. Fetches matching content from
confluence_markdown.jsonl file.

Usage:
    python data_format.py [project_id] [output_file.xlsx]
"""

# =============================================================================
#                           IMPORTS
# =============================================================================

import pandas as pd
import time
import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from pathlib import Path

from config import PROJECT_IDS
from fetch_tasks import _get_tasks_from_label_studio

# =============================================================================
#                           CONFIGURATION PARAMETERS
# =============================================================================

# Default paths
DEFAULT_CONFLUENCE_DATA_PATH = "/Users/rishabh.singh/Desktop/markdown_filter/filter/data/confluence_markdown.jsonl"
DEFAULT_OUTPUT_FILE = "label_studio_export_v4.xlsx"

# Confluence fields to extract (excluding markdown_body)
CONFLUENCE_FIELDS = [
    'owned_by_name',
    'autocomplete',
    'created_at',
    'type',
    'title',
    'body',
    'space',
    'url',
    'updated_at',
    'owned_by_email',
    'connector_type',
    '_document_hash',
    'id',
    '_timestamp',
    'space_id',
    'status',
    'space_url',
    '_allow_access_control'
]

# Confluence markdown data cache
_CONFLUENCE_MARKDOWN_CACHE = None

# =============================================================================
#                           DATA LOADING FUNCTIONS
# =============================================================================

def load_confluence_markdown_data(jsonl_path: str) -> Dict[str, Dict]:
    """
    Load confluence_markdown.jsonl file and create an indexed cache.
    
    Args:
        jsonl_path: Path to the confluence_markdown.jsonl file
        
    Returns:
        Dictionary with URL as key and full record as value
    """
    global _CONFLUENCE_MARKDOWN_CACHE
    
    if _CONFLUENCE_MARKDOWN_CACHE is not None:
        return _CONFLUENCE_MARKDOWN_CACHE
    
    print(f"Loading Confluence markdown data from: {jsonl_path}")
    cache = {}
    
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    url = record.get('url', '')
                    page_id = record.get('id', '')
                    
                    # Index by URL (normalized)
                    if url:
                        normalized_url = url.strip().rstrip('/')
                        cache[normalized_url] = record
                    
                    # Also index by page ID for easier lookup
                    if page_id:
                        cache[f"id:{page_id}"] = record
                        
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line {line_num}: {e}")
                    continue
        
        _CONFLUENCE_MARKDOWN_CACHE = cache
        print(f"✓ Loaded {len(cache)} Confluence pages into cache")
        return cache
        
    except FileNotFoundError:
        print(f"Warning: Confluence markdown file not found: {jsonl_path}")
        return {}
    except Exception as e:
        print(f"Error loading Confluence markdown data: {e}")
        return {}

# =============================================================================
#                           URL EXTRACTION FUNCTIONS
# =============================================================================

def extract_url_from_label_studio(link_html: str) -> Optional[str]:
    """
    Extract URL from Label Studio task data.
    
    Args:
        link_html: String that might contain a Confluence <a href="..."> link.
        
    Returns:
        Extracted URL or None
    """
    if not link_html:
        return None
    
    # Extract URL from HTML link
    match = re.search(r'href\s*=\s*"([^"]+)"', link_html)
    if match:
        return match.group(1).strip()
    
    # Check if it's already a URL
    if link_html.startswith("http"):
        return link_html.strip()
    
    return None


def extract_page_id_from_url(url: str) -> Optional[str]:
    """
    Extract page ID from Confluence URL.
    
    Args:
        url: Confluence URL
        
    Returns:
        Page ID or None
    """
    if not url:
        return None
    
    # Pattern 1: /pages/123456/Page+Title or /pages/123456
    match = re.search(r'/pages/(\d+)(?:/|$)', url)
    if match:
        return match.group(1)
    
    # Pattern 2: ?pageId=123456
    match = re.search(r'[?&]pageId=(\d+)', url)
    if match:
        return match.group(1)
    
    return None

# =============================================================================
#                           CONFLUENCE DATA LOOKUP
# =============================================================================

def lookup_confluence_data(url: str, markdown_cache: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Look up Confluence page data from the markdown cache.
    Returns exact fields from confluence_markdown.jsonl (excluding markdown_body).

    Args:
        url: Confluence page URL
        markdown_cache: Dictionary cache of Confluence markdown data

    Returns:
        Dict containing all Confluence fields with original field names
    """
    result = {'lookup_status': 'not_found'}
    
    if not url or not markdown_cache:
        result['lookup_status'] = 'no_url_or_cache'
        return result
    
    # Normalize URL for lookup
    normalized_url = url.strip().rstrip('/')
    
    # Try to find by exact URL match
    record = markdown_cache.get(normalized_url)
    
    # If not found, try to extract page ID and search by ID
    if not record:
        page_id = extract_page_id_from_url(url)
        if page_id:
            record = markdown_cache.get(f"id:{page_id}")
    
    # If found, extract all fields from confluence_markdown.jsonl (excluding markdown_body)
    if record:
        for key, value in record.items():
            if key != 'markdown_body':  # Exclude markdown_body
                result[key] = value
        result['lookup_status'] = 'found'
    else:
        result['lookup_status'] = 'not_found_in_cache'
    
    return result

# =============================================================================
#                           ANNOTATOR RESPONSE EXTRACTION
# =============================================================================

def extract_annotator_responses(task: Dict) -> List[Dict[str, Any]]:
    """
    Extract all annotator responses from a Label Studio task.
    Returns a list of dictionaries (one per annotator).
    """
    responses = []
    annotations = task.get("annotations", [])

    for idx, annotation in enumerate(annotations, 1):
        annot = {
            'annotator_number': idx,
            'annotator_id': annotation.get('completed_by', ''),
            'annotation_id': annotation.get('id', ''),
            'created_at': annotation.get('created_at', ''),
            'updated_at': annotation.get('updated_at', '')
        }

        for result in annotation.get('result', []):
            from_name = result.get('from_name', '')
            value = result.get('value', {})

            if 'choices' in value:
                annot[f'annotation_{from_name}'] = ', '.join(value['choices'])
            elif 'text' in value:
                text_val = value['text']
                annot[f'annotation_{from_name}'] = text_val[0] if isinstance(text_val, list) else text_val
            elif isinstance(value, dict):
                annot[f'annotation_{from_name}'] = json.dumps(value)
            else:
                annot[f'annotation_{from_name}'] = str(value)

        responses.append(annot)

    return responses

# =============================================================================
#                           TASK EXTRACTION
# =============================================================================

def extract_task_to_confluence_format(task: Dict, markdown_cache: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Extract Confluence data and annotator responses for each task.
    
    Args:
        task: Label Studio task
        markdown_cache: Cached Confluence markdown data
        
    Returns:
        Dictionary containing Confluence data and annotator responses
    """
    data = task.get("data", {})
    base = {}

    # Store Label Studio task ID
    base['label_studio_task_id'] = task.get('id')

    # --- Extract URL from Label Studio task ---
    link_field = data.get('text') or data.get('url') or data.get('space_url') or data.get('body')
    url = extract_url_from_label_studio(link_field) if link_field else None

    # --- Look up Confluence data from cache (confluence_markdown.jsonl) ---
    if url:
        confluence_data = lookup_confluence_data(url, markdown_cache)
        base.update(confluence_data)
    else:
        base['lookup_status'] = 'no_url_in_task'

    # --- Extract annotator responses ---
    responses = extract_annotator_responses(task)
    base['annotator_count'] = len(responses)

    for idx, annot in enumerate(responses, 1):
        # Extract all annotation fields into a single response
        annotation_data = {}
        for key, value in annot.items():
            if key.startswith('annotation_'):
                # Remove 'annotation_' prefix for cleaner keys
                field_name = key.replace('annotation_', '')
                annotation_data[field_name] = value
        
        # Store the complete annotation response as JSON string or empty string if no annotations
        base[f"annotator{idx}"] = json.dumps(annotation_data) if annotation_data else ""

    return base

# =============================================================================
#                           DATAFRAME CONVERSION
# =============================================================================

def extract_all_tasks_to_dataframe(tasks: List[Dict], markdown_cache: Dict[str, Dict]) -> pd.DataFrame:
    """
    Extract all tasks to a DataFrame with Confluence data and annotator responses.
    Each task is one row; annotator responses are in columns annotator1, annotator2, etc.
    """
    rows = []
    for task in tasks:
        row = extract_task_to_confluence_format(task, markdown_cache)
        rows.append(row)
    return pd.DataFrame(rows)

# =============================================================================
#                           TASK FETCHING
# =============================================================================

def fetch_tasks(project_ids: List[int]) -> List[Dict]:
    all_tasks = []
    for pid in project_ids:
        tasks = _get_tasks_from_label_studio(pid)
        all_tasks.extend(tasks)
    return all_tasks

# =============================================================================
#                           MAIN EXTRACTOR FUNCTION
# =============================================================================

def run_data_extractor(
    project_ids: Optional[List[int]] = None, 
    output_file: str = DEFAULT_OUTPUT_FILE,
    confluence_markdown_path: Optional[str] = None
):
    """
    Main function to extract Label Studio data with Confluence content.
    
    Args:
        project_ids: List of Label Studio project IDs
        output_file: Path to output Excel file
        confluence_markdown_path: Path to confluence_markdown.jsonl file
    """
    if project_ids is None:
        project_ids = PROJECT_IDS
    
    # Default path to confluence_markdown.jsonl
    if confluence_markdown_path is None:
        possible_paths = [DEFAULT_CONFLUENCE_DATA_PATH]
        
        for path in possible_paths:
            if Path(path).exists():
                confluence_markdown_path = path
                break
        
        if confluence_markdown_path is None:
            print("⚠ Warning: No confluence_markdown.jsonl file found!")
            print(f"   Searched in: {possible_paths}")
            confluence_markdown_path = possible_paths[0]  # Use first path anyway

    print("=" * 70)
    print("LABEL STUDIO DATA EXTRACTOR - CONFLUENCE + ANNOTATOR RESPONSES")
    print("=" * 70)
    print(f"Projects: {project_ids}")
    print(f"Output file: {output_file}")
    print(f"Confluence data: {confluence_markdown_path}\n")

    # Step 1: Load Confluence markdown data
    print("[1/3] Loading Confluence markdown data...")
    start = time.time()
    markdown_cache = load_confluence_markdown_data(confluence_markdown_path)
    print(f"✓ Loaded cache in {time.time() - start:.2f}s\n")

    # Step 2: Fetch tasks
    print("[2/3] Fetching tasks...")
    start = time.time()
    tasks = fetch_tasks(project_ids)
    print(f"✓ Fetched {len(tasks)} tasks in {time.time() - start:.2f}s")

    if not tasks:
        print("⚠ No tasks found!")
        return

    # Step 3: Extract data and export
    print("\n[3/3] Extracting data and exporting...")
    start = time.time()
    
    # Extract data
    df = extract_all_tasks_to_dataframe(tasks, markdown_cache)
    print(f"✓ Extracted {len(df)} rows and {len(df.columns)} columns")
    
    # Print lookup statistics
    if 'lookup_status' in df.columns:
        lookup_stats = df['lookup_status'].value_counts()
        print(f"\n  Lookup statistics:")
        for status, count in lookup_stats.items():
            print(f"    - {status}: {count}")
    
    # Save to Excel
    df.to_excel(output_file, index=False)
    print(f"\n✓ Saved to {output_file}")
    
    # Save to JSONL
    jsonl_file = output_file.replace('.xlsx', '.jsonl')
    with open(jsonl_file, 'w', encoding='utf-8') as f:
        for _, row in df.iterrows():
            json.dump(row.to_dict(), f, ensure_ascii=False)
            f.write('\n')
    print(f"✓ Saved to {jsonl_file}")
    print("=" * 70)
    
    return df

# =============================================================================
#                           MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    run_data_extractor(
        project_ids=PROJECT_IDS,
        output_file=DEFAULT_OUTPUT_FILE
    )
