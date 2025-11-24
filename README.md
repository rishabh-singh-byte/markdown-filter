# Confluence Page Quality Analyzer

An intelligent system for automatically detecting gibberish and low-quality content in Confluence documentation pages using advanced markdown analysis and priority-based decision-making.

---

## 📋 Project Summary

The **Confluence Page Quality Analyzer** is a comprehensive tool designed to automatically identify and filter out gibberish, incomplete, or low-quality Confluence pages from a large documentation corpus. The system analyzes both table content and regular page content to make intelligent decisions about page usefulness.

### Key Objectives

- **Automated Quality Detection**: Classify Confluence pages as "USEFUL" or "GIBBERISH" without manual review
- **Content Preservation**: Ensure valuable content with links, images, or meaningful text is never incorrectly flagged
- **Scalable Analysis**: Process thousands of pages efficiently using asynchronous batch processing
- **Human-Validated**: Integrated with Label Studio for ground truth annotations and model evaluation

### Use Cases

- Clean up large Confluence instances by identifying abandoned or incomplete pages
- Improve search results by filtering out low-quality documentation
- Generate quality metrics for documentation health monitoring
- Provide recommendations for page cleanup or archival

---

## 🧠 Core Logic & Approach

The system employs a **hierarchical, priority-based decision framework** that evaluates content in a specific order to maximize accuracy and minimize false positives.

### Architecture Overview

```
                ┌─────────────────────────────────────────────────────────────────┐
                │                    CONFLUENCE HTML INPUT                        │
                │                 (confluence_markdown.jsonl)                     │
                └────────────────────────────┬────────────────────────────────────┘
                                             │
                                             ▼
                                    HTML → Markdown Conversion
                                    (Preserves structure & content)
                                             │
                                             ▼
                                    Document Analysis & Metrics
                                    (Tables, words, links, images)
                                             │
                                             ▼
                              ┌──────────────┴──────────────┐
                              ▼                             ▼
                      Table-Level Analysis          Page-Level Analysis
                      (Priority-Based System)       (Content Aggregation)
                              │                             │
                              └──────────────┬──────────────┘
                                             ▼
                                      FINAL DECISION
                                    (USEFUL / GIBBERISH)
```

### Decision Logic

#### **Table-Level Analysis** (table_logic.py)

Tables are analyzed using a **priority-based system** that checks high-value indicators first:

**USEFUL if ANY of these conditions are met:**

1. **Priority 1 - High-Value Content** (Immediate USEFUL)
   - Contains links (hyperlinks to other pages/resources)
   - Contains file references/attachments
   - Contains images
   - Contains user mentions (`@username`)

2. **Priority 2 - Rich Cell Content** (Immediate USEFUL)
   - Any single cell has >5 meaningful words

3. **Priority 3 - Meaningful Words** (Threshold-Based)
   - ≥3 meaningful words (excluding placeholders like "TBD", "yes", "no")

**GIBBERISH if ANY of these structural issues are detected:**

1. **Structural Patterns**
   - Only header row filled (all data rows empty)
   - Only first column filled (all other columns empty)
   - Only ONE row or column filled (anywhere in table)
   - Zero meaningful words

2. **Size-Adaptive Analysis**
   - Very Small (n×2): Key-value table analysis
   - Small (2-5 rows/cols): Simplified metrics
   - Medium (6-15 rows/cols): Detailed analysis
   - Large (>15 rows/cols): Comprehensive analysis

#### **Page-Level Analysis** (page_decider.py)

After analyzing all tables, the entire page is evaluated:

**USEFUL if ANY of these conditions are met:**

1. At least **1 useful table** is present
2. Content outside tables has:
   - ≥30 meaningful words (excluding headings)
   - Any links
   - Any images
   - Any file references
   - Any user mentions

**Otherwise: GIBBERISH**

### Algorithm Strengths

- **No False Positives on Valuable Content**: Any page with links, images, or substantial text is preserved
- **Efficient Short-Circuit Evaluation**: Stops checking as soon as a USEFUL condition is met
- **Context-Aware**: Different analysis depth based on table size
- **Transparent Reasoning**: Every decision includes a detailed explanation

---

## 📁 File Structure Overview

```
markdown_filter/
├── README.md                           # This file
├── DATA_README.md                      # Comprehensive data documentation
│
├── filter/
│   ├── data/
│   │   └── confluence_markdown.jsonl   # Source: 10,359 Confluence pages
│   │
│   ├── main/                           # Core analysis pipeline
│   │   ├── conversion3.py              # HTML → Markdown converter
│   │   ├── check_markdown.py           # Markdown structure analyzer
│   │   ├── collect.py                  # Data aggregation module
│   │   ├── table_logic.py              # Table quality analyzer (priority-based)
│   │   ├── page_decider.py             # Page-level gibberish detector
│   │   ├── decider.py                  # Single page test script
│   │   ├── decider_label_studio.py     # Batch processor (async)
│   │   ├── metrics.py                  # Model evaluation & metrics
│   │   └── README.md                   # Pipeline documentation
│   │
│   ├── label_studio/                   # Annotation integration
│   │   ├── config.py                   # API configuration
│   │   ├── fetch_tasks.py              # Task fetcher from Label Studio
│   │   ├── data_format.py              # Data enrichment with Confluence content
│   │   ├── data/                       # Raw annotation tasks (614 pages)
│   │   ├── fetch_tasks/                # Processed annotations with ground truth
│   │   └── README.md                   # Label Studio workflow docs
│   │
│   └── results/                        # Model predictions & analysis
│       ├── label_studio_gibberish_results_3.jsonl
│       ├── label_studio_gibberish_results.xlsx
│       └── mispredictions.json
│
└── myev/                               # Python virtual environment
```

### Key Modules

| Module | Purpose | Input | Output |
|--------|---------|-------|--------|
| **conversion3.py** | HTML→Markdown conversion | Confluence HTML | Clean Markdown text |
| **check_markdown.py** | Extract structure & metrics | Markdown text | Tables, words, links, images |
| **collect.py** | Aggregate all analysis data | Document | Unified data dictionary |
| **table_logic.py** | Analyze table quality | Table analysis | USEFUL/GIBBERISH + reason |
| **page_decider.py** | Page-level decision | Document data | USEFUL/GIBBERISH + metrics |
| **decider_label_studio.py** | Batch processing | JSONL dataset | Predictions + results |
| **metrics.py** | Model evaluation | Predictions + labels | Accuracy, precision, recall |

---

## 🚀 Setup & Installation

### Prerequisites

- **Python**: 3.9 or higher
- **Operating System**: macOS, Linux, or Windows
- **Storage**: ~200MB for dependencies + ~100MB for data files

### Installation Steps

1. **Clone or navigate to the project directory**

```bash
cd /path/to/markdown_filter
```

2. **Create a virtual environment**

```bash
python3 -m venv myev
```

3. **Activate the virtual environment**

```bash
# macOS/Linux
source myev/bin/activate

# Windows
myev\Scripts\activate
```

4. **Install dependencies**

```bash
pip install beautifulsoup4 markdownify pandas openpyxl scikit-learn tqdm aiofiles
```

### Required Python Packages

```
beautifulsoup4>=4.12.0    # HTML parsing
markdownify>=0.11.6       # HTML to Markdown conversion
pandas>=2.0.0             # Data manipulation
openpyxl>=3.1.0           # Excel file support
scikit-learn>=1.3.0       # Model evaluation metrics
tqdm>=4.65.0              # Progress bars
aiofiles>=23.1.0          # Async file operations
```

### Data Setup

Ensure the main data file is in place:

```bash
# Verify data file exists
ls -lh filter/data/confluence_markdown.jsonl

# Expected: ~100MB+ file with 10,359 lines (one JSON per line)
```

---

## 💻 Usage Instructions

### 1. Quick Test - Single Page Analysis

Test the analyzer on a specific Confluence page by index:

```bash
cd /Users/rishabh.singh/Desktop/markdown_filter
python filter/main/page_decider.py
```

**Customize test index** by editing `filter/main/page_decider.py`:
```python
DEFAULT_TEST_INDEX = 100  # Change to any index (0-10358)
```

**Example Output:**
```
================================================================================
📄 PAGE ANALYSIS - Page 6933
================================================================================
✅ USEFUL PAGE
Decision: Useful: 1 useful table(s), 45 words outside tables

Page Metrics:
  📊 Tables: Total: 2 | Useful: 1 | Gibberish: 1
  📝 Content Outside Tables: 45 words, 3 links, 1 image
```

### 2. Test by Page ID and URL

Test with specific Confluence page ID and URL:

```bash
python filter/main/decider.py
```

Configure by editing `decider.py`:
```python
DEFAULT_PAGE_ID = 2635071834
DEFAULT_URL = "https://your-confluence-url.com/pages/..."
```

### 3. Detailed Table Analysis

Analyze table decision-making in detail:

```bash
python table_logic.py
```

**Output includes:**
- Priority content detection (links, files, images)
- Structural checks (empty rows/columns)
- Fill percentage analysis
- Row-by-row content breakdown
- Decision reasoning

### 4. Batch Processing

Process all annotated pages from Label Studio:

```bash
python filter/main/decider_label_studio.py
```

**Features:** Async batch processing (10 docs at a time), progress tracking, error handling per document

**Output:** `filter/results/label_studio_gibberish_results_3.jsonl`

**Configure batch size** by editing `decider_label_studio.py`:
```python
DEFAULT_BATCH_SIZE = 10  # Adjust as needed
```

### 5. Evaluate Model Performance

Calculate accuracy, precision, recall, and F1-score:

```bash
python filter/main/metrics.py
```

**Expected Output:** Overall accuracy: 84.2%, Precision (Gibberish): 88.5%, Recall (Gibberish): 91.2%

### 6. Debug Individual Components

Test specific pipeline stages:

```bash
python filter/main/conversion3.py       # HTML → Markdown conversion
python filter/main/check_markdown.py    # Document structure analysis
python filter/main/collect.py           # Data aggregation
```

### 7. Label Studio Integration

Fetch and enrich annotation tasks:

```bash
python filter/label_studio/fetch_tasks.py    # Fetch from API
python filter/label_studio/data_format.py    # Enrich with Confluence data
```

---

## 📊 Examples

### Example 1: Page with Links (USEFUL ✅)

**Input:** Table with 3 hyperlinks, empty cells elsewhere, no content outside table  
**Reason:** "Useful: 1 useful table(s) (3 links found)" — Links indicate navigation/reference value

---

### Example 2: Header-Only Table (GIBBERISH ❌)

**Input:**
```
| Name | Status | Date |
|------|--------|------|
|      |        |      |
```

**Reason:** "Only header row filled (rest empty)" — Table created but never populated

---

### Example 3: Rich Content Page (USEFUL ✅)

**Input:** 45-word paragraph about deployment, 2 embedded images, 1 incomplete table  
**Reason:** "Useful: 45 words outside tables, 2 images" — Substantial text and images preserved

---

### Example 4: Placeholder Table (GIBBERISH ❌)

**Input:**
```
| Item   | Value |
|--------|-------|
| Status | TBD   |
| Owner  | TBD   |
```

**Reason:** "0 meaningful words (excluding placeholders)" — Only placeholder content

---

### Example 5: Key-Value Configuration (USEFUL ✅)

**Input:**
```
| Configuration   | Value                  |
|-----------------|------------------------|
| Database Host   | prod-db-01.example.com |
| Port            | 5432                   |
| Connection Pool | 50                     |
```

**Reason:** "15 meaningful words in values column" — Key-value tables analyzed by values column

---

### Example 6: Mixed Content (USEFUL ✅)

**Input:** "Last updated: Jan 2025" + table with 30% filled cells + "@john.doe for questions"  
**Reason:** "Useful table (8 meaningful words) + 1 user mention" — Multiple signals combine

---

### Example 7: Single-Column Table (GIBBERISH ❌)

**Input:**
```
| Tasks  |
|--------|
| Item 1 |
|        |
```

**Reason:** "Only 1 column filled (anywhere in table)" — Incomplete table structure

---

## 📝 Notes & Assumptions

### Design Decisions

1. **Priority-Based Over Scoring**
   - The system uses **short-circuit evaluation** rather than weighted scoring
   - Once a USEFUL indicator is found, evaluation stops
   - Rationale: Faster processing and clearer reasoning

2. **Conservative USEFUL Classification**
   - **Philosophy**: "When in doubt, keep it"
   - False positives (marking gibberish as useful) are preferred over false negatives
   - Rationale: Losing valuable documentation is worse than keeping some low-quality pages

3. **Header Exclusion**
   - Table headers are **excluded** from fill percentage and word count calculations
   - Rationale: Headers are metadata, not content

4. **Placeholder Word List**
   - Words like "TBD", "TODO", "yes", "no", "N/A" are not counted as meaningful
   - List defined in `table_logic.py`

5. **Size-Adaptive Analysis**
   - Different analysis depth based on table dimensions
   - Rationale: Balance between accuracy and performance

6. **Threshold Tuning**
   - `MEANINGFUL_WORDS_THRESHOLD = 3` (tables)
   - `WORDS_OUTSIDE_TABLES_THRESHOLD = 30` (pages)
   - These were empirically determined from annotated dataset

### Assumptions

1. **Data Quality**
   - Confluence HTML is well-formed (valid XHTML storage format)
   - Pages have valid URLs and IDs

2. **Content Semantics**
   - Links indicate relationships or references (always valuable)
   - Images indicate visual documentation (always valuable)
   - User mentions indicate collaboration/ownership (valuable)

3. **Gibberish Patterns**
   - Incomplete tables follow predictable structural patterns
   - Empty or single-row/column tables are incomplete drafts

4. **Language**
   - Content is primarily in English
   - Word tokenization uses whitespace splitting

5. **Performance**
   - Processing 10,000+ pages requires async/batch processing
   - In-memory caching of Confluence data is acceptable (~500MB)

### Known Limitations

1. **Language Detection**: No multi-language support; assumes English content
2. **Context Awareness**: Cannot determine if a "TBD" page is intentionally temporary
3. **Semantic Understanding**: Doesn't understand if text is actually meaningful (e.g., "Lorem ipsum" would count as words)
4. **Table Type Classification**: Treats all tables equally (doesn't distinguish data tables from layout tables)
5. **Temporal Context**: No consideration of page age or update frequency

---

## 📚 Additional Documentation

| Document | Description |
|----------|-------------|
| **[DATA_README.md](DATA_README.md)** | Data distribution: 10,359 source pages, 614 annotated pages, model results |
| **[filter/main/README.md](filter/main/README.md)** | Pipeline workflow: module dependencies, configuration, common workflows |
| **[filter/label_studio/README.md](filter/label_studio/README.md)** | Annotation integration: Label Studio setup, task fetching, data enrichment |

---

## 🔧 Development Guidelines

When making changes to the codebase:

1. **Test Changes**: Use `page_decider.py` on multiple test indices (0-10358)
2. **Validate Metrics**: Run `metrics.py` to ensure accuracy isn't degraded
3. **Update Documentation**: Keep README files synchronized with code changes
4. **Preserve Logic**: Ensure existing decision logic and thresholds remain intact unless intentionally modified

---

## 📊 Performance Benchmarks

- **Processing Speed**: ~100 pages/second (async batch processing)
- **Memory Usage**: ~500MB (with full Confluence cache in memory)
- **Accuracy**: 84.2% on 614 annotated pages
- **Precision (Gibberish)**: 88.5%
- **Recall (Gibberish)**: 91.2%

---

## ❓ Troubleshooting

If you encounter issues:

1. **Check Data Files**: Verify `confluence_markdown.jsonl` exists and is not corrupted
2. **Review Sub-Documentation**: See `filter/main/README.md` for pipeline-specific details
3. **Test Individual Components**: Use `decider.py` or `page_decider.py` to debug specific pages
4. **Adjust Thresholds**: Modify constants in `table_logic.py` and `page_decider.py` if needed
5. **Check Dependencies**: Ensure all required packages are installed with correct versions

---
