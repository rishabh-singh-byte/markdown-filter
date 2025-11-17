# Data Distribution Guide

Documentation of all data files in the `markdown_filter` project.

---

## 📁 Directory Structure

```
markdown_filter/
├── filter/
│   ├── data/                           # Source Confluence pages (10,359)
│   ├── label_studio/
│   │   ├── data/                      # Raw project tasks (614)
│   │   └── fetch_tasks/               # Processed annotations (614)
│   └── results/                       # Model predictions (614)
└── DATA_README.md
```

---

## 📊 Quick Overview

| Directory | Records | Description |
|-----------|---------|-------------|
| **`filter/data/`** | 10,359 | All Confluence pages (source) |
| **`filter/label_studio/data/`** | 614 | Raw annotation tasks |
| **`filter/label_studio/fetch_tasks/`** | 614 | Enriched with Confluence data |
| **`filter/results/`** | 614 | Model predictions + analysis |

---

## 1️⃣ Source Data: `filter/data/`

### confluence_markdown.jsonl
**All Confluence pages from the organization**

- **Records**: 10,359 pages
- **Format**: JSONL (one JSON per line)
- **Size**: ~100+ MB

#### Key Fields
```json
{
  "id": "page_id",
  "title": "Page Title",
  "body": "<confluence-html>...</confluence-html>",
  "url": "https://confluence.com/pages/123456",
  "space": "ENGINEERING",
  "space_id":25xxxxxxxx
  "owned_by_name": "John Doe",
  "owned_by_email": "john@example.com",
  "created_at": "2020-07-09T08:08:28.839Z",
  "updated_at": "2021-03-15T14:22:10.123Z"
}
```

**Usage:**
```python
import json
with open("filter/data/confluence_markdown.jsonl") as f:
    pages = [json.loads(line) for line in f]
```

---

## 2️⃣ Label Studio Annotations: `filter/label_studio/`

### A. Raw Project Data: `filter/label_studio/data/`

Annotation tasks exported from Label Studio projects.

| File | Records | Project | Description |
|------|---------|---------|-------------|
| `tasks_projectId_46.json` | 123 | **Confluence Page Quality v1** | Quality check version 1 |
| `tasks_projectId_47.json` | 182 | **Meeting Notes v4** | Meeting notes quality check (v4) |
| `tasks_projectId_50.json` | 60 | **Confluence Page Quality v2** | Quality check version 2 |
| `tasks_projectId_51.json` | 249 | **Confluence Page Quality v3** | Quality check version 3 |
| **Total** | **614** | **4 projects** | Combined annotation dataset |

### B. Processed Data: `filter/label_studio/fetch_tasks/`

Enriched annotations with Confluence content merged and extracted from source data from the url extracted from the label studio data.

#### Main Files

| File | Format | Records | Description |
|------|--------|---------|-------------|
| `label_studio_export_v1.*` | JSONL/XLSX | 123 | v1 with Confluence data |
| `label_studio_export_v2.*` | JSONL/XLSX | 182 | Meeting notes with data |
| `label_studio_export_v3.*` | JSONL/XLSX | 60 | v2 with Confluence data |
| `label_studio_export_v4.*` | JSONL/XLSX | 249 | v3 with Confluence data |
| `label_studio_combined.jsonl` | JSONL | 614 | All projects merged |
| `label_studio_combined_processed.*` | JSONL/XLSX | 614 | **Final processed dataset for analysis** |

#### Data Schema
```json
{
  "label_studio_task_id": 30975,
  "lookup_status": "found",
  
  // From Confluence cache
  "id": "page_id",
  "title": "Page Title",
  "url": "https://confluence.com/pages/123",
  "body": "<html>...</html>",
  "space": "ENGINEERING",
  
  // Annotations
  "annotator_count": 2,
  "annotation": "yes",     // Ground truth (majority vote)
  "annotator1": "yes",
  "annotator2": "yes"
}
```
Note : Only the annotation which are in majority are considered, the one which are not in majority are left empty

#### Statistics
- **Total annotated**: 614 pages
- **Annotator agreement**: 77% (perfect), 23% (majority)
- **Cache lookup success**: 95%
- **Label distribution**: 65% gibberish, 35% useful

---

## 3️⃣ Model Results: `filter/results/`

Model predictions and error analysis on annotated data.

| File | Records | Description |
|------|---------|-------------|
| `label_studio_gibberish_results_3.jsonl` | 614 | Model predictions vs ground truth |
| `label_studio_gibberish_results.xlsx` | 614 | Excel format for analysis |
| `mispredictions.json` | 137 | Detailed error analysis |

### Schema
```json
{
  "id": "page_id",
  "title": "Page Title",
  "url": "https://confluence.com/pages/123",
  "annotation": "yes",              // Ground truth
  "result": {
    "is_gibberish": "yes",          // Model prediction
    "reason": "Gibberish: No useful tables, only 5 words outside tables",
    "decision_info": {
      "useful_table_count": 0,
      "words_outside_tables": 5,
      "links_outside_tables": 0
    }
  }
}
```

---

## 📈 Data Flow

```
confluence_markdown.jsonl (10,359 pages)
           │
           ├──────────────────────────────┐
           │                              │
           ▼                              ▼
    Label Studio(Ground Truth)      Full Pipeline
    ────────────                    ─────────────
    • 614 pages selected            • HTML → Markdown
    • 2-3 annotators each           • Table and other data extraction 
    • Merged with source            • Content analysis
    • Ground truth labels           • Gibberish detection
           │                              │
           └──────────┬───────────────────┘
                      ▼
              Model Predictions
              ─────────────────
              • Results (614)

```

---

## 🔍 Usage Examples

### Load Source Data
```python
import json

# Load all Confluence pages
with open("filter/data/confluence_markdown.jsonl") as f:
    pages = [json.loads(line) for line in f]

# Access specific page
page = pages[100]
print(f"Title: {page['title']}")
```

### Load Annotated Data
```python
# Load annotations with ground truth
with open("filter/label_studio/fetch_tasks/label_studio_combined_processed.jsonl") as f:
    annotated = [json.loads(line) for line in f]

# Filter by label
gibberish = [p for p in annotated if p['annotation'] == 'yes']
useful = [p for p in annotated if p['annotation'] == 'no']
```

### Load Model Results
```python
# Load predictions
with open("filter/results/label_studio_gibberish_results_3.jsonl") as f:
    results = [json.loads(line) for line in f]

# Compare prediction vs ground truth
correct = [r for r in results if r['result']['is_gibberish'] == r['annotation']]
accuracy = len(correct) / len(results)
```

---

## 🚀 Quick Commands

```bash
# Count records
wc -l filter/data/confluence_markdown.jsonl              # 10,359
wc -l filter/label_studio/fetch_tasks/label_studio_combined.jsonl  # 614
wc -l filter/results/label_studio_gibberish_results_3.jsonl        # 614

# View samples
head -1 filter/data/confluence_markdown.jsonl | python -m json.tool
head -5 filter/label_studio/data/tasks_projectId_46.json

# Search by URL
grep "specific-page-url" filter/data/confluence_markdown.jsonl
```

---

## 📋 Project Timeline

| Version | Date | Project | Records | Description |
|---------|------|---------|---------|-------------|
| v1 | Nov 2024 | Page Quality v1 | 123 | Initial quality annotations |
| v4 | Dec 2024 | Meeting Notes v4 | 182 | Meeting notes focus |
| v2 | Jan 2025 | Page Quality v2 | 60 | Second validation round |
| v3 | Jan 2025 | Page Quality v3 | 249 | Final comprehensive set |
| **Combined** | Jan 2025 | **All Projects** | **614** | **Complete dataset** |

---

## 🔗 Related Documentation

- **[Processing Pipeline](filter/main/README.md)** - Analysis modules and workflow
- **[Label Studio Integration](filter/label_studio/README.md)** - Annotation process
- **[HTML Converter](filter/main/conversion3.py)** - Confluence to Markdown

---

**Last Updated:** January 6, 2025  
**Total Data**: 10,359 source pages, 614 annotated

