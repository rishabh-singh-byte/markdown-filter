# Confluence Page Analysis Pipeline

Complete workflow for analyzing Confluence pages, converting HTML to Markdown, and detecting gibberish content.

---

## 📋 Pipeline Overview

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
│  Files: table_decider.py + page_decider.py                      │
│                                                                 │
│  4a. Table-Level Decision (table_decider.py)                    │
│      • Checks meaningful words (≥3)                             │
│      • Checks for links, images, files, mentions                │
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

**Flow:** HTML → Markdown → Analysis → Detection → Evaluation

---

## 📦 Modules

### 1️⃣ conversion3.py
**Convert Confluence HTML to Markdown**

#### What it does
Converts Confluence Storage Format (XHTML) into clean Markdown text, handling:
- Tables (colspan/rowspan expansion)
- Confluence macros (code, expand, status, jira)
- User mentions `[~username]`
- Images and attachments
- Nested lists and structures
- Date formatting in table cells

#### How it works
1. Parses HTML with BeautifulSoup
2. Recursively converts nodes to Markdown
3. Handles special Confluence elements
4. Cleans and normalizes whitespace

#### Configuration
```python
DEFAULT_CONFLUENCE_DATA_PATH = "/path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 6687
```

#### How to run
```bash
python conversion3.py
```

#### When to use
- Test HTML to Markdown conversion on a specific record
- Debug conversion issues
- Validate Markdown output quality

---

### 2️⃣ check_markdown.py
**Analyze Markdown documents**

#### What it does
Analyzes converted Markdown to extract structured information:
- Tables (content, dimensions, fill percentage)
- Document structure (headings, paragraphs, lists)
- Content metrics (words, links, images, mentions)
- Separate counts for content inside/outside tables

#### How it works
1. Converts HTML to Markdown (calls `conversion3.py`)
2. Extracts tables using regex patterns
3. Analyzes table content (words, links, images)
4. Analyzes document structure
5. Generates summary statistics

#### Key functions
- `extract_tables_from_markdown()` - Extracts all tables
- `analyze_table_content()` - Analyzes individual tables
- `analyze_markdown_structure()` - Analyzes document structure
- `summarize_document()` - Generates complete summary

#### Configuration
```python
DEFAULT_DATA_FILE = "/path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 100
```

#### How to run
```bash
python check_markdown.py
```

#### When to use
- Understand document structure
- Verify table extraction accuracy
- Debug analysis logic
- Inspect content metrics

---

### 3️⃣ collect.py
**Aggregate analysis data**

#### What it does
Collects all document analysis data into a unified dictionary:
- Document metadata (id, title, url)
- All tables with individual analysis
- Word counts (total, in tables, outside tables)
- Content counts (links, images, files, mentions)
- Useful vs gibberish table classification

#### How it works
1. Takes a document as input
2. Calls `check_markdown.py` for analysis
3. Processes each table with `table_decider.py`
4. Aggregates metrics into single dictionary
5. Returns comprehensive data structure

#### Output structure
```python
{
    "id": "page_id",
    "title": "Page Title",
    "url": "page_url",
    "num_tables": 3,
    "tables": [...],
    "table_word_count": 150,
    "total_word_count": 250,
    "word_count_excluding_tables": 100,
    "useful_table_count": 2,
    "gibberish_table_count": 1,
    # ... more fields
}
```

#### Configuration
```python
DEFAULT_DATA_FILE = "/path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 2000
```

#### How to run
```bash
python collect.py
```

#### When to use
- Test data collection pipeline
- Verify aggregated metrics
- Debug metric calculations
- Inspect complete document data

---

### 4️⃣ table_decider.py
**Detect gibberish tables**

#### What it does
Determines if a table contains useful information or is gibberish.

#### Decision logic
A table is **USEFUL** if it has ANY of:
- ≥3 meaningful words (excludes: draft, tbd, yes, no, empty cells)
- Any links
- Any images
- Any file references
- Any user mentions

Otherwise, it's **GIBBERISH**.

#### How it works
1. Receives table analysis from `collect.py`
2. Counts meaningful words (excludes placeholders)
3. Checks for links, images, files, mentions
4. Returns decision + reason

#### Configuration
```python
DEFAULT_DATA_FILE = "/path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 150
MEANINGFUL_WORDS_THRESHOLD = 3
```

#### How to run
```bash
python table_decider.py
```

#### When to use
- Test table classification logic
- Adjust meaningful word threshold
- Debug false positives/negatives
- Understand table decisions

**Example output:**
```
Table 0 is ✅ Useful
  Decision: Useful: 15 meaningful words (excl. headings & placeholders)
  Metrics:
    • Meaningful Words: 15
    • Links: 2
    • Images: 0
```

---

### 5️⃣ page_decider.py
**Detect gibberish pages**

#### What it does
Determines if an entire Confluence page contains useful information or is gibberish.

#### Decision logic
A page is **USEFUL** if it has ANY of:
- ≥1 useful table (from `table_decider.py`)
- ≥20 words outside tables (excluding headings)
- Any links outside tables
- Any images outside tables
- Any file references outside tables
- Any user mentions outside tables

Otherwise, it's **GIBBERISH**.

#### How it works
1. Receives document data from `collect.py`
2. Checks for useful tables
3. Checks content outside tables
4. Returns decision + detailed info

#### Configuration
```python
DEFAULT_DATA_FILE = "/path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 100
WORDS_OUTSIDE_TABLES_THRESHOLD = 20
```

#### How to run
```bash
# Use default test index
python page_decider.py

# Test specific index
python page_decider.py 250
```

#### When to use
- Test page-level classification
- Adjust threshold parameters
- Debug false positives/negatives
- Analyze specific pages

**Example output:**
```
================================================================================
📄 PAGE ANALYSIS - Page 100
================================================================================
URL: https://confluence.example.com/page/123
Title: Project Documentation

✅ USEFUL PAGE
Decision: Useful: 1 useful table(s), 45 words outside tables

Page Metrics:
  📊 Tables:
    • Total: 2
    • Useful: 1
    • Gibberish: 1
  📝 Content Outside Tables:
    • Words: 45
    • Links: 3
    • Images: 1
```

---

### 6️⃣ decider.py
**Test specific page by ID and URL**

#### What it does
Quick test script for analyzing a specific Confluence page by its ID and URL.

#### How it works
1. Loads all documents
2. Finds page by ID and URL
3. Runs complete analysis pipeline
4. Displays results

#### Configuration
```python
DEFAULT_DATA_FILE = "/path/to/confluence_markdown.jsonl"
DEFAULT_PAGE_ID = 2635071834
DEFAULT_URL = "https://confluence.example.com/pages/..."
```

#### How to run
```bash
python decider.py
```

#### When to use
- Test a specific known page
- Debug particular page issues
- Validate pipeline on real examples

---

### 7️⃣ decider_label_studio.py
**Batch process annotated data**

#### What it does
Processes all Label Studio annotated pages asynchronously and generates predictions.

#### How it works
1. Loads annotated data from Label Studio export
2. Processes each document through pipeline
3. Runs gibberish detection
4. Saves results with predictions
5. Uses async processing for speed

#### Features
- Async batch processing (10 documents at a time)
- Progress bars with tqdm
- Error handling per document
- JSONL output format

#### Configuration
```python
DEFAULT_INPUT_FILE = "/path/to/label_studio_combined_processed.jsonl"
DEFAULT_OUTPUT_FILE = "/path/to/label_studio_gibberish_results.jsonl"
DEFAULT_BATCH_SIZE = 10
```

#### How to run
```bash
python decider_label_studio.py
```

#### When to use
- Process all annotated pages
- Generate predictions for evaluation
- Run production pipeline on dataset
- Compare model vs human annotations

**Output format:**
```json
{
    "id": "page_id",
    "title": "Page Title",
    "url": "page_url",
    "annotation": "yes",
    "result": {
        "is_gibberish": "yes",
        "reason": "Gibberish: No useful tables, only 5 words outside tables"
    }
}
```

---

### 8️⃣ metrics.py
**Calculate model performance**

#### What it does
Evaluates model predictions against human annotations and calculates metrics.

#### Metrics calculated
- **Accuracy** - Overall correctness
- **Precision** - Gibberish prediction accuracy
- **Recall** - Gibberish detection rate
- **F1-Score** - Balanced performance
- **Confusion Matrix** - Detailed breakdown
- **Classification Report** - Per-class metrics

#### How it works
1. Loads results from `decider_label_studio.py`
2. Extracts ground truth (annotations) and predictions
3. Calculates all metrics using scikit-learn
4. Displays formatted results

#### Configuration
```python
DEFAULT_INPUT_FILE = "/path/to/label_studio_gibberish_results.jsonl"
```

#### How to run
```bash
python metrics.py
```

#### When to use
- Evaluate model performance
- Compare different approaches
- Measure impact of threshold changes
- Generate performance reports

**Example output:**
```
Overall Accuracy: 84.2%

Precision:
  • Gibberish: 88.5%
  • Useful: 78.3%

Recall:
  • Gibberish: 91.2%
  • Useful: 72.1%

Confusion Matrix:
              Predicted
              Yes    No
Actual  Yes   365    33
        No     48    168
```

---

## 🔧 Configuration Guide

All scripts have configuration at the top:

```python
# =============================================================================
#                           CONFIGURATION PARAMETERS
# =============================================================================

# Data path
DEFAULT_DATA_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/data/confluence_markdown.jsonl"

# Test indices
DEFAULT_TEST_INDEX = 100

# Thresholds
MEANINGFUL_WORDS_THRESHOLD = 3        # table_decider.py
WORDS_OUTSIDE_TABLES_THRESHOLD = 20   # page_decider.py

# Processing
DEFAULT_BATCH_SIZE = 10               # decider_label_studio.py
```

**To modify:**
1. Open the Python file
2. Edit values in CONFIGURATION PARAMETERS section
3. Save and run

---

## 🚀 Common Workflows

### Workflow 1: Test single page
```bash
# By index
python page_decider.py 100

# By ID and URL
python decider.py
```
**Use case:** Quick testing, debugging specific pages

---

### Workflow 2: Process annotated dataset
```bash
# 1. Process all pages
python decider_label_studio.py

# 2. Calculate metrics
python metrics.py
```
**Use case:** Evaluate model performance, generate results

---

### Workflow 3: Debug conversion/analysis
```bash
# 1. Test conversion
python conversion3.py

# 2. Test analysis
python check_markdown.py

# 3. Test collection
python collect.py
```
**Use case:** Debug pipeline components, verify output

---

### Workflow 4: Adjust thresholds
```bash
# 1. Edit table_decider.py → MEANINGFUL_WORDS_THRESHOLD
# 2. Edit page_decider.py → WORDS_OUTSIDE_TABLES_THRESHOLD
# 3. Re-run pipeline
python decider_label_studio.py
python metrics.py

# 4. Compare results
```
**Use case:** Optimize detection thresholds

---

## 📊 Module Dependencies

```
conversion3.py          (standalone - no dependencies)
        │
        ▼
check_markdown.py       (imports: conversion3)
        │
        ▼
collect.py             (imports: check_markdown)
        │
        ├──────────────┬──────────────┐
        ▼              ▼              ▼
table_decider.py   decider.py   decider_label_studio.py
        │              │              │
        ▼              │              │
page_decider.py ◄──────┘              │
        │                             │
        └─────────────────────────────┘
                      │
                      ▼
                 metrics.py
```

**Import hierarchy:**
1. `conversion3.py` - No dependencies
2. `check_markdown.py` - Uses `conversion3`
3. `collect.py` - Uses `check_markdown`
4. `table_decider.py` - Uses `collect`
5. `page_decider.py` - Uses `collect`, `table_decider`
6. `decider.py` - Uses `collect`, `page_decider`
7. `decider_label_studio.py` - Uses `collect`, `page_decider`
8. `metrics.py` - Standalone (uses sklearn)

---

## 📝 Quick Reference

| Task | Command | Purpose |
|------|---------|---------|
| Test conversion | `python conversion3.py` | Verify HTML → Markdown |
| Analyze page | `python check_markdown.py` | Extract metrics |
| Collect data | `python collect.py` | Test aggregation |
| Check table | `python table_decider.py` | Test table logic |
| Check page | `python page_decider.py [index]` | Test page logic |
| Test specific | `python decider.py` | Test by ID/URL |
| Process batch | `python decider_label_studio.py` | Run on dataset |
| Calculate metrics | `python metrics.py` | Evaluate performance |

---

## 🎯 Key Features

- ✅ **Modular Design** - Independent components
- ✅ **Easy Configuration** - All parameters at top
- ✅ **Standalone Testing** - Each module runs independently
- ✅ **Async Processing** - Fast batch operations
- ✅ **Clear Output** - Well-formatted results
- ✅ **Comprehensive Metrics** - Full evaluation suite

---

## 🔗 Related Documentation

- **[Data Guide](../../DATA_README.md)** - Complete data documentation
- **[Label Studio](../label_studio/README.md)** - Annotation workflow

---

**Last Updated:** January 7, 2025
