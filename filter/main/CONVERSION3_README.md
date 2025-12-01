# Confluence HTML to Markdown Converter

> **Module:** `conversion3.py`  
> **Purpose:** Convert Confluence Storage Format (XHTML) to clean, analyzable Markdown

---

## 📑 Table of Contents

- [Quick Start](#-quick-start)
- [What Gets Converted](#-what-gets-converted)
- [Confluence Macros](#-confluence-macros)
- [HTML & Confluence Elements](#-html--confluence-elements)
- [Output Format](#-output-format)
- [Technical Details](#-technical-details)
- [Troubleshooting](#-troubleshooting)
- [Configuration](#-configuration)

---

## 🚀 Quick Start

```python
from filter.main.conversion3 import convert_html_to_markdown

# Convert Confluence HTML to Markdown
html = """<ac:structured-macro ac:name="code">
    <ac:parameter ac:name="language">python</ac:parameter>
    <ac:plain-text-body>print("Hello")</ac:plain-text-body>
</ac:structured-macro>"""

markdown = convert_html_to_markdown(html)
# Output: ```python\nprint("Hello")\n```
```

**Testing:** `python conversion3.py` (edit `DEFAULT_TEST_INDEX` for different documents)

**Key Features:**
- ✅ 35+ Confluence macros + generic fallback
- ✅ Smart tables (colspan, dates with 6+ formats, macros prioritized in cells)
- ✅ Defensive (never crashes, always returns output)
- ✅ Analysis-ready output (links, mentions, files tracked)
- ✅ Metadata capture (ac: and data- attributes from macros)

---

## ✅ What Gets Converted

### Quick Reference

**✅ KEPT & CONVERTED:**
- **Content Macros** → Markdown (code, expand, status, panel, tasks)
- **Reference Macros** → `[*-REF: ...]` (jira, include, children, viewpdf)
- **HTML** → Standard Markdown (headings, lists, tables, links, images, code)
- **Confluence Elements** → Special formats (mentions: `[~user]`, emoticons, dates)
- **Unknown Macros** → `[MACRO: name ...]` (preserved, not lost)

**❌ SKIPPED (content extracted):**
- **UI Decoration** → info, note, tip, warning, success, error boxes
- **Interactive Widgets** → livesearch, create-from-template
- **Navigation** → toc, table-of-contents (→ `<!-- TOC omitted -->`)
- **Non-Content** → script, style, ac:placeholder, span.text-placeholder, span.placeholder-inline-tasks

**Rule:** If it contains or references content → converted. If purely decorative → skipped but content kept.

### Conversion Examples

```html
<!-- ✅ Content Macro -->
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="title">In Progress</ac:parameter>
</ac:structured-macro>
→ [STATUS: In Progress]

<!-- ❌ UI Decoration (content kept, box removed) -->
<ac:structured-macro ac:name="info">
  <ac:rich-text-body><p>This is important</p></ac:rich-text-body>
</ac:structured-macro>
→ This is important

<!-- ✅ Unknown Macro (preserved) -->
<ac:structured-macro ac:name="custom-widget">
  <ac:parameter ac:name="type">chart</ac:parameter>
</ac:structured-macro>
→ [MACRO: custom-widget (type=chart)]
```

---

## 🔷 Confluence Macros

### What Are Confluence Macros?

XML-like tags that add dynamic functionality:

```xml
<ac:structured-macro ac:name="macro-name">
  <ac:parameter ac:name="key">value</ac:parameter>
  <ac:rich-text-body>Content</ac:rich-text-body>
</ac:structured-macro>
```

**Components:** `ac:name` (type), `ac:parameter` (config), `ac:rich-text-body`/`ac:plain-text-body` (content)

---

### Complete Macro Reference (35+ Types)

| Macro Name | Type | Markdown Output | Analysis |
|------------|------|----------------|----------|
| **code**, **code-block** | Content | ` ```language\ncode``` ` | Words |
| **expand**, **details** | Content | `<details><summary>title</summary>body</details>` (no body fallback) | Words |
| **status** | Content | `[STATUS: title]` | Words |
| **panel** | Content | `> **Panel (color):**\n> content` | Words |
| **task-list**, **tasklist** | Content | `- [x]` / `- [ ]` (empty tasks skipped) | Words |
| **jira**, **jira-issues**, **jira-issue** | Reference | `[JIRA-REF: server - project]` or `N issues [JIRA: project]` (extracts project from JQL) | **Link** |
| **include**, **include-page**, **excerpt-include**, **excerpt** | Reference | `[INCLUDE-REF: page (Space: space)]` | **Link** |
| **children** | Reference | `[PAGE-REF: Child pages list]` | **Link** |
| **content-by-label**, **contentbylabel** | Reference | `[PAGE-REF: Pages with labels - X]` | **Link** |
| **content-report-table** | Reference | `[PAGE-REF: title in spaces (labels: X)]` | **Link** |
| **recently-updated** | Reference | `[PAGE-REF: Recently updated pages in spaces]` | **Link** |
| **index** | Reference | `[PAGE-REF: Page index]` | **Link** |
| **viewpdf**, **view-file**, **viewfile** | File | `[PDF: file]` / `[Attachment: file]` | **File** |
| **attachments** | File | `[ATTACHMENTS: Dynamic file viewer (with upload/layout)]` | **File** |
| **roadmap**, **roadmap-planner** | Complex | `[MACRO: Roadmap (params)]` | Words |
| **toc**, **table-of-contents** | Navigation | `<!-- TOC omitted -->` | *(skipped)* |
| **info**, **note**, **tip**, **warning**, **success**, **error** | UI Only | *(content extracted, box removed)* | *(skipped)* |
| **livesearch**, **create-from-template** | UI Only | *(skipped entirely)* | *(skipped)* |
| **[unknown]** | Generic | `[MACRO: name (params) -> body]` + metadata | Words |

**Categories:**
- Content (8): User-created content → full markdown
- Reference (13): Links to other content → placeholder with details
- File (4): Attachments → file references
- Complex (2): Advanced features → generic placeholder
- Navigation (2): Auto-generated → comment
- UI (8): Styling/interactive only → content kept or skipped
- Unknown (1): Future-proof fallback → never lose content

---

## 📋 HTML & Confluence Elements

### Standard HTML

| Element | Markdown Output | Notes |
|---------|----------------|-------|
| `<h1>`-`<h6>` | `#` to `######` | Headings |
| `<strong>`, `<b>` | `**bold**` | Text formatting |
| `<em>`, `<i>` | `*italic*` | Text formatting |
| `<ul>`, `<ol>` | `-`, `1.` | Lists (nested with 2-space indent) |
| `<a>` | `[text](url)` | Links (preserves `mailto:`) |
| `<img>` | `![alt](src)` | Images |
| `<table>` | Markdown table | Auto-detects headers, handles colspan |
| `<pre>`, `<code>` | ` ```code``` ` | Code blocks |
| `<p>`, `<div>`, `<section>` | Plain text | Block containers |
| `<script>`, `<style>` | *(skipped)* | No content value |

### Confluence-Specific Tags

| Tag | Output | Notes |
|-----|--------|-------|
| `<ac:link>` + `<ri:user>` | `[~username]` | User mentions (supports multiple attributes) |
| `<ac:image>` + `<ri:attachment>` | `![caption](filename)` | Attachment images |
| `<ac:emoticon>` | Unicode emoji | ✅ 📋 💭 ⭐ ⚠️ ℹ️ (7+ emojis mapped) |
| `<ac:task>` + `<ac:task-status>` | `- [x]` / `- [ ]` | Task checkboxes (empty tasks skipped) |
| `<ac:task-list>` | `- [x]` / `- [ ]` | Task lists in any context (table cells, etc.) |
| `<ac:adf-extension>` | `[ADF-CONTENT: ...]` or empty | Decision lists, ADF content (placeholders removed) |
| `<time datetime="">` | Formatted date | Auto-detected with 6+ formats (ISO, slash, dash, text) |
| `<ac:placeholder>` | *(skipped)* | Editor hints |
| `<span class="text-placeholder">` | *(skipped)* | Instructional placeholder text |
| `<span class="placeholder-inline-tasks">` | *(skipped)* | Task placeholder text |

---

## 📤 Output Format

### Bracket Notation (Special Elements)

All special content uses brackets for easy parsing:

| Format | Type | Counted As |
|--------|------|------------|
| `[STATUS: text]` | Status badge | Content |
| `[JIRA-REF: ...]` | Jira reference | **Link** |
| `[INCLUDE-REF: page]` | Page inclusion | **Link** |
| `[PAGE-REF: ...]` | Page relationship | **Link** |
| `[PDF: filename]` | PDF attachment | **File** |
| `[Attachment: name]` | File attachment | **File** |
| `[~username]` | User mention | **Mention** |
| `[MACRO: name ...]` | Unknown macro | Content |

### Standard Markdown

- ` ```language\ncode``` ` - Code blocks
- `| cell | cell |` - Tables
- `- [x]` / `- [ ]` - Task checkboxes
- `![alt](src)` - Images
- `[text](url)` - Links
- `<details><summary>...</summary></details>` - Expandable sections

---

## 🔍 Special Macro Implementations

### JIRA Macro
Extracts project name from JQL queries for more meaningful output:
- **With count=true**: `"N issues [JIRA: ProjectName]"` (displays as count in Confluence)
- **Without count**: `"[JIRA-REF: server - ProjectName]"` (full issue list)
- **JQL parsing**: Extracts project name from `project = "Name"` patterns
- **Fallback**: Uses server name if project extraction fails

### Attachments Macro
Dynamic file viewer that loads files at render time:
- **Storage format**: Only contains macro definition (no file list)
- **Parameters**: `upload` (enables upload), `data-layout` (viewer layout)
- **Output**: `[ATTACHMENTS: Dynamic file viewer (with upload/layout)]`

### Expand/Details Macro
**Critical Change:** Does NOT fall back to body text to prevent status leakage:
- **Title source**: ONLY uses explicit `title` or `label` parameters
- **Rationale**: Prevents Confluence "status" macros inside expand from leaking text like "DRAFT"
- **Output**: `<details><summary>title</summary>body</details>` or `<details>body</details>`

### Task List Macro
Filters out empty tasks (only placeholders):
- **Empty detection**: Removes `<ac:placeholder>` before checking text
- **Skip criteria**: Tasks with no real content after placeholder removal
- **Contexts**: Handles both `<ac:task-list>` and standalone `<ac:task>` elements

### Content Report Table Macro
Dynamic table of pages matching criteria:
- **Parameters**: `labels`, `spaces`, `blankTitle`
- **Output**: `[PAGE-REF: title in spaces (labels: X)]`
- **Use case**: Confluence generates table at render time; storage only has definition

### ADF Extension
Handles decision lists and ADF (Atlassian Document Format) content:
- **Processing**: Removes all `<ac:placeholder>` and `<ac:adf-attribute>` elements
- **Output**: `[ADF-CONTENT: preview...]` if content remains, empty string if only placeholders
- **Attributes**: Ignores `local-id`, `state`, etc. (metadata only)

---

## 🗓️ Date Extraction

### Supported Date Formats (6+ Patterns)

The `_extract_and_format_date()` function handles multiple date formats:

| Pattern | Example | Regex |
|---------|---------|-------|
| **ISO** | 2023-01-15 | `\d{4}-\d{2}-\d{2}` |
| **Slash (ISO)** | 2023/01/15 | `\d{4}/\d{2}/\d{2}` |
| **Slash (US)** | 01/15/2023, 1/15/2023 | `\d{1,2}/\d{1,2}/\d{4}` |
| **Dash (US)** | 01-15-2023 | `\d{1,2}-\d{1,2}-\d{4}` |
| **Text (abbrev)** | Jan 15, 2023 | Month name patterns |
| **Text (day-first)** | 15 Jan 2023 | Month name patterns |

### Priority in Table Cells
1. **Check for macros first** - If cell contains `<ac:structured-macro>`, process normally
2. **Try date extraction** - Only if no macros present
3. **Fallback to normal** - Process cell content normally if no date found

### Confluence `<time>` Elements
- **Attribute**: `datetime` (ISO format) → parsed and formatted as `YYYY-MM-DD`
- **Fallback**: Visible text in `<time>` element
- **Error handling**: Returns original text if parsing fails

---

## 🔧 Technical Details

### Processing Priority (High → Low)

1. **Macros** - Processed as complete units first
2. **Confluence Special** - ac:placeholder, ac:emoticon, ac:link, ac:image
3. **Structural** - table, ul/ol, h1-h6, pre/code
4. **Block** - p, div, section
5. **Inline** - a, img, strong, em

### Macro Processing Pipeline

```
1. Detect <ac:structured-macro> or <ac:macro>
2. Extract parameters → {key: value} via <ac:parameter>
3. Extract metadata → {ac:*, data-*} attributes (macro-id, schema-version, layout, etc.)
4. Extract body (rich-text → plain-text → fallback)
5. Apply conversion (specific OR generic placeholder)
6. Return markdown (may include metadata comments)
```

**Key Functions:**
- `_extract_macro_params()` - Extracts `<ac:parameter>` elements into dict
- `_extract_macro_metadata()` - Captures `ac:` and `data-` attributes (new feature)
- `_extract_macro_body()` - Gets rich-text or plain-text body with fallback
- `_render_macro()` - Converts to markdown with specific or generic handler

### Table Features

- **Header Detection** - Uses `<th>` tags to identify header rows
- **Colspan Expansion** - Adds empty cells for colspan > 1 (rowspan not yet supported)
- **Key-Value Detection** - Special format for 2-column tables (all rows have exactly 2 cells)
- **Date Auto-Format** - 6+ patterns: ISO (2023-01-15), slash (2023/01/15, 01/15/2023), dash (01-15-2023), text (Jan 15, 2023, 15 Jan 2023)
- **Macro Priority** - Processes macros in cells BEFORE date extraction (prevents macro params being treated as dates)
- **Caption** - `<caption>` → bold text above table
- **Pipe Escaping** - All `|` characters in cells escaped as `\|` for valid Markdown

### Whitespace Cleaning

- Replace `\xa0` → space, remove `\u200b`
- Unescape HTML entities (`&nbsp;`, `&lt;`)
- Collapse 3+ newlines → max 2
- Remove trailing spaces (except before `|` in tables)
- **Function:** `_clean_whitespace(s, keep_newlines=False)` - Controls line break preservation for tables/structured content

### Utility Functions

| Function | Purpose | Key Features |
|----------|---------|--------------|
| `_clean_whitespace()` | Normalize whitespace | `keep_newlines` parameter for tables; HTML unescape |
| `_escape_pipe()` | Escape pipes in tables | `\|` escaping for valid Markdown tables |
| `_extract_and_format_date()` | Extract dates from cells | 6+ patterns (ISO, slash, dash, text); handles `<time>` elements |
| `_extract_macro_params()` | Get macro parameters | Extracts `<ac:parameter>` into `{name: value}` dict |
| `_extract_macro_metadata()` | Get macro metadata | Captures `ac:*` and `data-*` attributes (macro-id, layout, etc.) |
| `_extract_macro_body()` | Get macro content | Rich-text → plain-text → fallback hierarchy |
| `_users_from_ac_link()` | Extract user mentions | Multiple attribute fallbacks; formats as `[~user]` |

---

## 🛡️ Error Handling

### Philosophy

> **Never Crash** - Return imperfect markdown over failing  
> **Preserve Content** - Extract text if structure can't convert  
> **Generic Handler** - No macro is completely lost

### Fallback Strategies

| Component | Primary | Fallback |
|-----------|---------|----------|
| **Parser** | `html.parser` | `lxml` |
| **User Mention** | `ri:account-id` | `username`, `ri:username` |
| **Macro Body** | `ac:rich-text-body` | `ac:plain-text-body`, all content |
| **Date Parse** | `datetime.parse()` | Original text |
| **Code Block** | Structured extraction | Text fallback |

---

## 🐛 Troubleshooting

| Issue | What You See | Solution |
|-------|-------------|----------|
| Unknown macro | `[MACRO: unknown ...]` | Generic placeholder preserves content |
| Table issues | Misaligned cells | Colspan expanded; macros processed first |
| Missing mentions | Plain text | Falls back to link text |
| Extra blank lines | 3+ newlines | Post-processing collapses to max 2 |

**Debugging Tips:**
1. Check input is valid Confluence XHTML
2. Search for `[MACRO:` to find unsupported macros
3. All special content uses `[TYPE: ...]` format
4. Run standalone: `python conversion3.py`
5. Check for empty tasks - tasks with only placeholders are automatically skipped
6. Details/expand macros don't fall back to body text (prevents status leakage)

---

## ⚙️ Configuration

```python
DEFAULT_CONFLUENCE_DATA_PATH = "/path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 10131  # Updated test record
_UI_MACROS = {
    "info", "note", "tip", "warning", "success", "error",  # Admonition boxes
    "livesearch",  # Search widget
    "create-from-template",  # Template creation button
}
```

**Add New Macro Support:**
1. Add case to `_render_macro()` function (around line 516)
2. Extract parameters via `params` dict and body via `body_html`
3. Extract metadata via `metadata` dict (optional)
4. Return markdown format (use bracket notation for placeholders)
5. Document in this README under "Complete Macro Reference"

---

## 📊 Statistics

| Category | Count |
|----------|-------|
| **Confluence Macros** | 35+ (8 content + 13 reference + 4 file + 2 complex + 2 navigation + 8 UI + 1 generic) |
| **HTML Elements** | 20+ (h1-h6, p, div, ul, ol, table, a, img, strong, em, pre, code) |
| **Confluence Tags** | 10+ (ac:link, ac:image, ac:emoticon, ac:task, ac:task-list, ac:adf-extension, ac:parameter, ac:placeholder, span placeholders) |
| **Actively Converted** | 29 types (26 macros + HTML + Confluence tags) |
| **Skipped** | 10 types (8 UI boxes/widgets + 2 navigation + script/style) |

**Output Categories for Analysis:**
- **Links** - URLs, JIRA-REF, INCLUDE-REF, PAGE-REF
- **Files** - PDF, Attachments
- **Mentions** - `[~username]`
- **Images** - `![alt](src)`
- **Content** - Text, headings, code, tables, tasks

---

## 📚 Related Documentation

- **[Main README](../../README.md)** - Project overview
- **[Pipeline README](README.md)** - Complete analysis pipeline
- **[check_markdown.py](check_markdown.py)** - Markdown analysis
- **[table_logic.py](table_logic.py)** - Table quality analysis

---

## 🎯 Design Principles

**Conversion Philosophy:**
1. **Content First** - Preserve all meaningful content
2. **Skip Decoration Only** - Only skip pure UI elements
3. **Readable Placeholders** - Clear `[TYPE: content]` format
4. **Defensive Coding** - Fallbacks for everything
5. **Analysis-Ready** - Output optimized for analysis

**Decision Logic:**
```
Does it contain user content? → ✅ CONVERT
Does it reference content? → ✅ CONVERT to placeholder
Is it auto-generated? → ❌ SKIP with comment
Is it pure decoration? → ❌ SKIP (keep inner content)
Unknown element? → ✅ CONVERT with generic fallback
```

**Default:** When in doubt, preserve it.

---

## 📝 Recent Changes & Updates

### Version History

**Latest Updates:**
- ✅ Added 4 new macros: `attachments`, `content-report-table`, `recently-updated`, `livesearch`, `create-from-template`
- ✅ Enhanced JIRA macro with project name extraction from JQL
- ✅ Added metadata capture (`_extract_macro_metadata()`) for all macros
- ✅ Implemented robust date extraction with 6+ patterns for table cells
- ✅ Added `ac:adf-extension` handling for decision lists
- ✅ Enhanced task list filtering (empty tasks skipped)
- ✅ Fixed expand/details macro to prevent status leakage
- ✅ Added placeholder filtering for `span.text-placeholder` and `span.placeholder-inline-tasks`
- ✅ Improved table cell processing with macro priority over dates

**Macro Count:** 31 → 35+ supported macros

**Configuration Changes:**
- `DEFAULT_TEST_INDEX`: 7193 → 10131
- `_UI_MACROS`: 6 → 8 types

---
