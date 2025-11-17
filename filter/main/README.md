# Analysis Pipeline - Module Documentation

**Purpose**: Step-by-step pipeline for converting Confluence HTML pages to Markdown, analyzing content, and detecting gibberish/low-quality pages.

**Quick Summary**: HTML → Markdown → Extract Metrics → Analyze Tables → Decide Page Quality → Evaluate Performance

---

## 🔄 Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONFLUENCE HTML INPUT                        │
│                 (confluence_markdown.jsonl)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: HTML to Markdown Conversion                            │
│  ────────────────────────────────────                           │
│  File: conversion3.py                                           │
│  Function: convert_html_to_markdown()                           │
│                                                                 │
│  Input:  HTML string from Confluence body field                 │
│  Output: Clean Markdown text                                    │
│  • Handles tables, lists, macros, code blocks                   │
│  • Preserves user mentions and attachments                      │
│  • Converts Confluence-specific elements                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Document Analysis                                      │
│  ─────────────────────────                                      │
│  File: check_markdown.py                                        │
│  Functions:                                                     │
│  • extract_tables_from_markdown() - Extract tables              │
│  • analyze_table_content() - Analyze each table                 │
│  • analyze_markdown_structure() - Analyze document              │
│  • summarize_document() - Generate summary                      │
│                                                                 │
│  Output:                                                        │
│  • Table metrics (words, links, images, mentions)               │
│  • Document structure (headings, paragraphs, lists)             │
│  • Content statistics (excluding headings/tables)               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Data Collection                                        │
│  ───────────────────────                                        │
│  File: collect.py                                               │
│  Function: collect_document_data()                              │
│                                                                 │
│  Aggregates all analysis data into single dictionary:           │
│  • Document metadata (id, title, url)                           │
│  • Table data with analysis                                     │
│  • Word counts (total, excluding tables)                        │
│  • Links, images, files, mentions counts                        │
│  • Structure summary                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Gibberish Detection                                    │
│  ────────────────────────────                                   │
│  Files: table_logic.py + page_decider.py                        │
│                                                                 │
│  4a. Table-Level Decision (table_logic.py)                      │
│      • Priority-based decision system                           │
│      • Checks meaningful words, priority content, structure     │
│      • Returns: is_gibberish (bool) + reason                    │
│                                                                 │
│  4b. Page-Level Decision (page_decider.py)                      │
│      • Checks for useful tables                                 │
│      • Checks words outside tables (≥20)                        │
│      • Checks content outside tables                            │
│      • Returns: is_gibberish (bool) + decision_info             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Output & Evaluation                                    │
│  ───────────────────────────                                    │
│  • decider.py - Test individual pages                           │
│  • decider_label_studio.py - Batch process with async           │
│  • metrics.py - Calculate accuracy, precision, recall           │
└─────────────────────────────────────────────────────────────────┘

Confluence HTML → Markdown → Analysis → Detection → Metrics
     ↓              ↓           ↓          ↓          ↓
conversion3.py  check_markdown  collect  page_decider  metrics.py
```

**Additional Tools**:
- `decider.py` - Test single page by ID/URL
- `decider_label_studio.py` - Batch process 614 annotated pages (async)
- `metrics.py` - Calculate accuracy, precision, recall against ground truth

---

## 📦 Core Modules

```
conversion3.py          (standalone - no dependencies)
        │
        ▼
check_markdown.py       (imports: conversion3)
        │
        ▼
    collect.py          (imports: check_markdown)
        │
        ├──────────────┬──────────────┐
        ▼              ▼              ▼
   table_logic.py  decider.py   decider_label_studio.py
        │              │              │
        ▼              │              │
page_decider.py ◄──────┘              │
        │                             │
        └─────────────────────────────┘
                      │
                      ▼
                 metrics.py
```

---

### 1. conversion3.py
**Purpose**: Convert Confluence HTML to Markdown

**Input**: HTML string from `body` field  
**Output**: Clean Markdown text

**Key Features**:
- Handles tables with colspan/rowspan
- Converts 12+ Confluence macros (code, expand, status, jira, include, task-list, panel, etc.)
- Preserves user mentions `[~username]`
- Extracts images and attachments
- Recognizes and formats dates in tables
- Skips UI-only macros (info, note, tip, warning)

**Usage**:
```bash
python conversion3.py
```

**Config**:
```python
DEFAULT_CONFLUENCE_DATA_PATH = "path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 7193
```

**📚 Detailed Documentation**: See **[CONVERSION3_README.md](CONVERSION3_README.md)** for:
- Complete macro reference (12+ types with examples)
- Conversion logic for each macro type
- Table handling (colspan, rowspan, key-value detection)
- Special elements (user mentions, emoticons, images)
- Design principles and troubleshooting

---

### 2. check_markdown.py
**Purpose**: Analyze Markdown and extract structured metrics

**Input**: Markdown text  
**Output**: Dictionary with tables, words, links, images, mentions

**What It Extracts**:
- **Tables**: Dimensions, content per cell, fill percentage
- **Document structure**: Headings, paragraphs, lists
- **Content metrics**: 
  - Words/links/images inside tables
  - Words/links/images outside tables (excluding headings)

**Key Functions**:
- `extract_tables_from_markdown()` - Regex-based table extraction
- `analyze_table_content()` - Per-table analysis (words, links, images)
- `analyze_markdown_structure()` - Document structure analysis
- `summarize_document()` - Complete summary generation

**Usage**:
```bash
python check_markdown.py
```

**Config**:
```python
DEFAULT_DATA_FILE = "path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 100
```

---

### 3. collect.py
**Purpose**: Aggregate all analysis data into unified dictionary

**Input**: Document object (from JSONL)  
**Output**: Comprehensive data dictionary

**Output Structure**:
```python
{
    "id": "page_id",
    "title": "Page Title",
    "url": "page_url",
    "num_tables": 3,
    "tables": [
        {
            "content": "...",
            "num_rows": 5,
            "num_cols": 3,
            "word_count": 42,
            "link_count": 2,
            "image_count": 0,
            "file_count": 1,
            "mention_count": 0,
            "fill_percentage": 67.5
        }
    ],
    "total_word_count": 250,
    "table_word_count": 150,
    "word_count_excluding_tables": 100,
    "links_outside_tables": 3,
    "images_outside_tables": 1,
    "files_outside_tables": 0,
    "mentions_outside_tables": 2
}
```

**Usage**:
```bash
python collect.py
```

**Config**:
```python
DEFAULT_DATA_FILE = "path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 2000
```

---

### 4. table_logic.py
**Purpose**: Classify individual tables as USEFUL or GIBBERISH

**Logic** (Priority-based, short-circuit evaluation):

**✅ USEFUL if ANY**:
1. **Priority Content**: Links, files, images, user mentions present
2. **Rich Cell**: Any cell has >5 meaningful words
3. **Threshold**: ≥3 meaningful words (excluding placeholders: TBD, yes, no, N/A)

**❌ GIBBERISH if ANY**:
1. Only header row filled (data rows empty)
2. Only first column filled
3. Only ONE row/column filled (anywhere)
4. Zero meaningful words

**❓ CAN'T DECIDE**:
- 1-2 meaningful words (ambiguous cases)

**Size-Adaptive Analysis**:
- **Very Small (n×2)**: Key-value table logic
- **Small (2-5 rows/cols)**: Simplified analysis
- **Medium (6-15)**: Detailed analysis
- **Large (>15)**: Comprehensive analysis

**Usage**:
```bash
python table_logic.py
```

**Config**:
```python
DEFAULT_TEST_INDEX = 150
MEANINGFUL_WORDS_THRESHOLD = 3
```

**Example Output**:
```
Table 0: ✅ USEFUL
Reason: 3 link(s) found (highest priority)
Metrics: 15 words | 3 links | 0 images | 67% fill
```

---

### 5. page_decider.py
**Purpose**: Classify entire page as USEFUL or GIBBERISH

**Logic**:

**✅ USEFUL if ANY**:
1. ≥1 useful table (from `table_logic.py`)
2. ≥30 words outside tables (excluding headings)
3. Links outside tables
4. Images outside tables
5. File references outside tables
6. User mentions outside tables

**❌ GIBBERISH**:
- None of the above conditions met

**Usage**:
```bash
# Default test index
python page_decider.py

# Custom index
python page_decider.py 250
```

**Config**:
```python
DEFAULT_TEST_INDEX = 6933
WORDS_OUTSIDE_TABLES_THRESHOLD = 30
```

**Example Output**:
```
================================================================================
📄 PAGE ANALYSIS - Page 6933
================================================================================
URL: https://confluence.example.com/pages/123456
Title: Project Documentation

✅ USEFUL PAGE
Reason: 1 useful table(s), 45 words outside tables

📊 Tables: 2 total (1 useful, 1 gibberish)
📝 Outside Tables: 45 words | 3 links | 1 image
```

---

### 6. decider.py
**Purpose**: Test specific page by ID and URL

**Usage**:
```bash
python decider.py
```

**Config**:
```python
DEFAULT_PAGE_ID = 2635071834
DEFAULT_URL = "https://confluence.example.com/pages/..."
```

**Use Case**: Debug a known problematic page

---

### 7. decider_label_studio.py
**Purpose**: Batch process all 614 annotated pages

**Features**:
- Async processing (10 pages at a time)
- Progress bars (tqdm)
- Error handling per page
- JSONL output

**Output Format**:
```json
{
    "id": "page_id",
    "title": "Page Title",
    "url": "page_url",
    "annotation": "yes",
    "result": {
        "is_gibberish": "yes",
        "reason": "Gibberish: No useful tables, only 5 words"
    }
}
```

**Usage**:
```bash
python decider_label_studio.py
```

**Config**:
```python
DEFAULT_INPUT_FILE = "../label_studio/fetch_tasks/label_studio_combined_processed.jsonl"
DEFAULT_OUTPUT_FILE = "../results/label_studio_gibberish_results_3.jsonl"
DEFAULT_BATCH_SIZE = 10
```

---

### 8. metrics.py
**Purpose**: Evaluate model vs human annotations

**Metrics**:
- Accuracy (overall correctness)
- Precision (gibberish prediction accuracy)
- Recall (gibberish detection rate)
- F1-Score (balanced performance)
- Confusion matrix

**Usage**:
```bash
python metrics.py
```

**Config**:
```python
DEFAULT_INPUT_FILE = "../results/label_studio_gibberish_results_3.jsonl"
```

**Example Output**:
```
Overall Accuracy: 84.2%

Precision: Gibberish 88.5% | Useful 78.3%
Recall:    Gibberish 91.2% | Useful 72.1%
F1-Score:  82.7%

Confusion Matrix:
              Predicted
              Gibberish  Useful
Actual  Gibberish   365     33
        Useful       48    168
```

---

## 🔧 Configuration Parameters

| Parameter | Module | Default | Purpose |
|-----------|--------|---------|---------|
| `DEFAULT_TEST_INDEX` | All | Varies | Document index to test (0-10358) |
| `MEANINGFUL_WORDS_THRESHOLD` | table_logic.py | 5 | Min words for useful table |
| `WORDS_OUTSIDE_TABLES_THRESHOLD` | page_decider.py | 30 | Min words for useful page |
| `DEFAULT_BATCH_SIZE` | decider_label_studio.py | 10 | Async batch size |

**To modify**: Edit the `CONFIGURATION PARAMETERS` section at the top of each Python file.

---

## 🚀 Common Workflows

### Workflow 1: Test Single Page
```bash
# By index
python page_decider.py 100

# By ID/URL
python decider.py
```

### Workflow 2: Evaluate Model
```bash
# Step 1: Process all annotated pages
python decider_label_studio.py

# Step 2: Calculate metrics
python metrics.py
```

### Workflow 3: Debug Pipeline
```bash
# Test each stage
python conversion3.py
python check_markdown.py
python collect.py
python table_logic.py
python page_decider.py
```

### Workflow 4: Tune Thresholds
```bash
# 1. Edit thresholds in table_logic.py and page_decider.py
# 2. Re-run batch processing
python decider_label_studio.py

# 3. Evaluate new performance
python metrics.py
```

---

## 📊 Module Dependencies

```
conversion3.py (standalone)
    ↓
check_markdown.py
    ↓
collect.py
    ↓
    ├─→ table_logic.py
    ↓
page_decider.py
    ↓
    ├─→ decider.py (single page test)
    ├─→ decider_label_studio.py (batch processing)
    ↓
metrics.py (evaluation)
```

**Import Order**:
1. `conversion3.py` - No dependencies
2. `check_markdown.py` - Imports `conversion3`
3. `collect.py` - Imports `check_markdown`
4. `table_logic.py` - Imports `collect`
5. `page_decider.py` - Imports `collect`, `table_logic`
6. `decider.py` / `decider_label_studio.py` - Import `page_decider`
7. `metrics.py` - Standalone (uses scikit-learn)

---

## 📋 Quick Reference

| Task | Command | Output |
|------|---------|--------|
| Test HTML conversion | `python conversion3.py` | Markdown text |
| Extract metrics | `python check_markdown.py` | Tables + word counts |
| Aggregate data | `python collect.py` | Unified dictionary |
| Analyze table | `python table_logic.py` | USEFUL/GIBBERISH |
| Analyze page | `python page_decider.py` | USEFUL/GIBBERISH |
| Test by ID | `python decider.py` | Single page result |
| Batch process | `python decider_label_studio.py` | 614 predictions |
| Evaluate | `python metrics.py` | Accuracy/Precision/Recall |

---

## 🎯 Decision Logic Summary

### Table-Level (table_logic.py)

**Decision Tree**:
```
Has links/images/files/mentions? → YES → ✅ USEFUL
                ↓ NO
Any cell >5 words? → YES → ✅ USEFUL
                ↓ NO
Only header filled? → YES → ❌ GIBBERISH
                ↓ NO
Only 1 row/col filled? → YES → ❌ GIBBERISH
                ↓ NO
≥3 meaningful words? → YES → ✅ USEFUL
                     → NO → ❌ GIBBERISH
```

### Page-Level (page_decider.py)

**Decision Logic**:
```
Has ≥1 useful table? → YES → ✅ USEFUL
                    ↓ NO
≥30 words outside tables? → YES → ✅ USEFUL
                          ↓ NO
Links/images/files/mentions outside? → YES → ✅ USEFUL
                                     ↓ NO
                                   ❌ GIBBERISH
```

---

## 🔗 Related Documentation

- **[Main README](../../README.md)** - Project overview and setup
- **[Data Guide](../../DATA_README.md)** - Dataset documentation (10,359 pages + 614 annotated)
- **[Label Studio](../label_studio/README.md)** - Annotation workflow

---
