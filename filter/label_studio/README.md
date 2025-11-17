# Label Studio Integration

Extract Label Studio tasks with Confluence content from cached data.

---

## Overview

This module integrates Label Studio annotation data with Confluence content through a cached lookup system:

- **Fast** - No API calls to Confluence, instant lookups from cache
- **Reliable** - No rate limits or network failures
- **Complete** - Access to all Confluence fields from cached data

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    LABEL STUDIO PROJECTS                        │
│                  (API: fetch_tasks.py)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Fetch Tasks                                            │
│  ───────────────────                                            │
│  • Connect to Label Studio API                                  │
│  • Fetch tasks with pagination                                  │
│  • Retrieve all annotations                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Load Confluence Cache                                  │
│  ─────────────────────────────                                  │
│  • Load confluence_markdown.jsonl                               │
│  • Index by URL and page ID                                     │
│  • Keep in memory for fast lookups                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Match & Extract                                        │
│  ───────────────────────                                        │
│  • Extract URLs from tasks                                      │
│  • Match with cached Confluence data                            │
│  • Extract annotator responses                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Export                                                 │
│  ──────────────                                                 │
│  • Excel: Complete dataset                                      │
│  • JSONL: Streamable format                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files

### config.py
**Purpose:** Centralized configuration

**Configuration:**
```python
# API Settings
LABEL_STUDIO_BASE_URL = "http://54.174.211.211:80"
LABEL_STUDIO_API_KEY = "your_api_key"

# Project IDs
RANKING_PROJECT_IDS = [61]
INTENT_PROJECT_IDS = [47]

# Evaluation Mode
RANKING_EVAL_MODE = "LOCAL"
```

---

### fetch_tasks.py
**Purpose:** Fetch tasks from Label Studio API

**Configuration:**
```python
PAGE_SIZE = 50
```

**Function:**
```python
_get_tasks_from_label_studio(project_id: int) -> List[Dict]
```

**Usage:**
```bash
python fetch_tasks.py
```

**Output:** Saves to `filter/label_studio/data/tasks_projectId_XX.json`

---

### data_format.py
**Purpose:** Extract tasks with Confluence content from cache

**Key Functions:**
```python
# Load Confluence cache (once)
load_confluence_markdown_data(jsonl_path: str) -> Dict[str, Dict]

# Extract URLs from tasks
extract_url_from_label_studio(link_html: str) -> Optional[str]
extract_page_id_from_url(url: str) -> Optional[str]

# Lookup content from cache
lookup_confluence_data(url: str, cache: Dict) -> Dict[str, Any]

# Extract annotator responses
extract_annotator_responses(task: Dict) -> List[Dict[str, Any]]

# Main extractor
run_data_extractor(
    project_ids: List[int],
    output_file: str,
    confluence_markdown_path: str
) -> pd.DataFrame
```

**Configuration:**
```python
DEFAULT_CONFLUENCE_DATA_PATH = "/path/to/confluence_markdown.jsonl"
DEFAULT_OUTPUT_FILE = "label_studio_export_v4.xlsx"
```

**Confluence Fields Retrieved:**
- `id`, `title`, `url`, `space`, `body`
- `owned_by_name`, `owned_by_email`
- `created_at`, `updated_at`, `status`
- `type`, `space_id`, `space_url`
- All other original fields

**Lookup Status Values:**
- `found` - Successfully found in cache
- `not_found_in_cache` - URL/ID not in cache file
- `no_url_in_task` - No URL in Label Studio task
- `no_url_or_cache` - Missing URL or cache

**Usage:**
```bash
python data_format.py
```

**Output:**
- `label_studio_export_vX.xlsx` - particular project dataset (excel format)
- `label_studio_export_vX.jsonl` - (JSONL format)

---

## Usage Examples

### Basic Extraction
```python
from data_format import run_data_extractor

df = run_data_extractor(
    project_ids=[46],
    output_file="export.xlsx"
)
```

### Custom Confluence Path
```python
df = run_data_extractor(
    project_ids=[46, 47, 50, 51],
    output_file="combined.xlsx",
    confluence_markdown_path="/custom/path/data.jsonl"
)
```

### Manual Lookup
```python
from data_format import (
    load_confluence_markdown_data,
    extract_url_from_label_studio,
    lookup_confluence_data
)

# Load cache once
cache = load_confluence_markdown_data("../data/confluence_markdown.jsonl")

# Extract URL and lookup
url = extract_url_from_label_studio('<a href="https://...">Link</a>')
result = lookup_confluence_data(url, cache)

if result['lookup_status'] == 'found':
    print(f"Title: {result['title']}")
    print(f"Space: {result['space']}")
```

---

## Output Format

### Excel (.xlsx)
Complete dataset with columns:
- `label_studio_task_id`
- `annotator_count`, `annotator1`, `annotator2`, ...
- All Confluence fields (`title`, `url`, `body`, `space`, etc.)
- `lookup_status`

### JSONL (.jsonl)
```json
{
  "label_studio_task_id": 30975,
  "title": "Example Page",
  "url": "https://confluence.com/pages/123456",
  "space": "ENGINEERING",
  "body": "<p>HTML content...</p>",
  "annotator1": "{...}",
  "lookup_status": "found"
}
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Fetch tasks | `python fetch_tasks.py` |
| Extract with Confluence data | `python data_format.py` |
| Update configuration | Edit `config.py` |
