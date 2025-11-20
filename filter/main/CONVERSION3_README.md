# Confluence HTML to Markdown Converter

**Module**: `conversion3.py`  
**Function**: `convert_html_to_markdown(html_str: str) -> str`  
**Purpose**: Convert Confluence Storage Format (XHTML) to clean Markdown while preserving meaningful content

---

## 🔄 Conversion Flow

```
Confluence XHTML → Parse (BeautifulSoup) → Identify Elements → Convert to Markdown → Clean & Format → Output
```

---

## 📋 Macro Conversion Reference

### Content Macros (Converted)

| Macro | Input | Output | Notes |
|-------|-------|--------|-------|
| **code**, code-block | `<ac:structured-macro ac:name="code">` + params | ` ```language\ncode``` ` | Extracts language param, wraps in fence |
| **expand**, details | `<ac:structured-macro ac:name="expand">` | `<details><summary>title</summary>body</details>` | Uses title param only (not body text) |
| **status** | `<ac:structured-macro ac:name="status">` | `[STATUS: title]` | Simple placeholder format |
| **task-list**, tasklist | `<ac:task>` elements | `- [x] task` or `- [ ] task` | Checkbox list format |
| **panel** | `<ac:structured-macro ac:name="panel">` | `> **Panel (color):**\n> content` | Blockquote format |

### Reference Macros (Placeholders)

| Macro | Output Format | Treated As |
|-------|---------------|------------|
| **include**, include-page, excerpt-include, excerpt | `[INCLUDE-REF: page (Space: space)]` | Link |
| **jira**, jira-issues, jira-issue | `[JIRA-REF: server - project]` or `N issues [JIRA: project]` | Link |
| **children** | `[PAGE-REF: Child pages list]` | Link |
| **content-by-label** | `[PAGE-REF: Pages with labels - labels]` | Link |
| **index** | `[PAGE-REF: Page index]` | Link |
| **viewpdf**, view-file, viewfile | `[PDF: filename]` or `[Attachment: filename]` | File |
| **roadmap**, roadmap-planner | `[MACRO: title (param=value)]` | Content |

### Navigation & Skipped Macros

| Macro | Output | Notes |
|-------|--------|-------|
| **toc**, table-of-contents | `<!-- TOC omitted -->` | Comment placeholder |
| **info**, note, tip, warning, success, error | *(skipped)* | Pure UI decoration |

### Generic Handler

Any unrecognized macro: `[MACRO: name params -> body_preview]`

---

## 🎨 HTML & Confluence Elements

### Standard HTML Elements

| Element | Markdown Output | Notes |
|---------|----------------|-------|
| `<h1>` - `<h6>` | `#` - `######` | Direct conversion |
| `<p>`, `<div>`, `<section>` | Plain text with spacing | Block containers |
| `<strong>`, `<b>` | `**text**` | Bold |
| `<em>`, `<i>` | `*text*` | Italic |
| `<ul>` / `<ol>` | `-` / `1.` lists | Nested (2-space indent) |
| `<a>` | `[text](url)` | Preserves mailto: |
| `<img>` | `![alt](src)` | Standard image |
| `<table>` | Markdown table | Handles colspan, dates, macros in cells |
| `<pre>`, `<code>` | ` ```\ncode``` ` | Native code blocks |
| `<script>`, `<style>` | *(skipped)* | No content value |

### Confluence-Specific Elements

| Element | Output | Notes |
|---------|--------|-------|
| `<ac:image>` + `<ri:attachment>` | `![caption](filename)` | Attachment images |
| `<ac:link>` + `<ri:user>` | `[~username]` | User mentions (tries multiple attrs) |
| `<ac:emoticon>` | Unicode emoji | Maps common names: ✅ 📋 💭 ⭐ ⚠️ ℹ️ |
| `<ac:placeholder>` | *(skipped)* | Editor hints only |
| `<time datetime="">` | Formatted date | Auto-detected in tables |

---

## 📊 Content Preservation for Analysis

| Element Type | Markdown Format | Analysis Category |
|--------------|-----------------|-------------------|
| Links, includes, jira, children, index | `[text](url)`, `[*-REF: ...]` | **Links** |
| Images | `![alt](src)` | **Images** |
| PDF/attachments | `[PDF: name]` | **Files** |
| User mentions | `[~username]` | **Mentions** |
| Tables | Markdown tables | **Tables** |
| Text, headings, code, tasks, status, panels | Various | **Words** |

---

## 🔧 Processing Details

### Macro Parsing Pipeline

1. **Identification**: Detect `<ac:structured-macro>` or `<ac:macro>` tags
2. **Parameters**: Extract `<ac:parameter ac:name="key">value</ac:parameter>` → dict
3. **Metadata**: Store `ac:macro-id`, `ac:schema-version` for debugging
4. **Body Extraction**:
   - `<ac:rich-text-body>` → Recursively convert nested HTML to Markdown
   - `<ac:plain-text-body>` → Extract plain text directly
   - Fallback → Extract all inner content
5. **Rendering**: Known macros → specific logic; Unknown → generic placeholder

### Element Processing Priority

1. **Macros** (highest) → Processed as complete units
2. **Special Confluence** → `ac:placeholder`, `ac:emoticon`, `ac:link`, `ac:image`
3. **Structural** → `table`, `ul/ol`, `h1-h6`, `pre/code`
4. **Block** → `p`, `div`, `section`
5. **Inline** (lowest) → `a`, `img`, `strong`, `em`, `b`, `i`

### Whitespace & Formatting

**Whitespace Cleaning** (`_clean_whitespace`):
- Replaces `\xa0` (non-breaking space) with regular space
- Removes `\u200b` (zero-width space)
- Unescapes HTML entities (`&nbsp;`, `&lt;`, etc.)
- When `keep_newlines=False`: Collapses all whitespace to single spaces
- When `keep_newlines=True`: Preserves newlines (for tables/code)

**Post-Processing**:
1. Collapse 3+ newlines → max 2 newlines
2. Remove trailing spaces (except before `|` in tables)
3. Ensure document ends with single newline

**Pipe Escaping**: `|` → `\|` in table cells

### Table Handling

- **Key-Value Detection**: 2-column tables → special format
- **Colspan Expansion**: `colspan="2"` → add empty cells
- **Header Detection**: Uses `<th>` tags
- **Caption**: `<caption>` → bold text above table
- **Date Detection**: Auto-formats dates in cells (ISO, slash, dash, text formats)
- **Macro Processing**: Processes macros in cells before conversion

### Date Detection

Supports: `2023-01-15`, `2023/01/15`, `01/15/2023`, `01-15-2023`, `Jan 15, 2023`, `15 Jan 2023`  
Priority: `<time datetime="">` attribute → regex pattern matching

---

## 🛡️ Error Handling

### Defensive Features

- **Parser fallback**: `html.parser` → `lxml` if needed
- **Attribute fallbacks**: Multiple attribute names tried (e.g., `ri:account-id`, `username`, `ri:username`)
- **Date parsing**: Wrapped in try/except, falls back to original text
- **Empty/None handling**: Returns empty string instead of crashing
- **Code blocks**: Exception handling with text extraction fallback
- **Macro body**: Tries rich-text → plain-text → all content
- **Tables**: Handles missing colspan/rowspan gracefully

### Philosophy

**Never Crash**: Return imperfect markdown over crashing  
**Preserve Content**: Extract text if structure can't be converted  
**Generic Handler**: No macro is completely lost

---

## 🚀 Usage

```python
from filter.main.conversion3 import convert_html_to_markdown

html = """<ac:structured-macro ac:name="code">
    <ac:parameter ac:name="language">python</ac:parameter>
    <ac:plain-text-body>print("Hello")</ac:plain-text-body>
</ac:structured-macro>"""

markdown = convert_html_to_markdown(html)
# Output: ```python\nprint("Hello")\n```
```

**Testing**: Run `python conversion3.py` (edit `DEFAULT_TEST_INDEX` for different records)

---

## 📖 Output Format Guide

### Brackets = References/Metadata
- `[STATUS: text]` → Status badge
- `[JIRA-REF: ...]` → Jira reference (counts as link)
- `[INCLUDE-REF: page]` → Included page (counts as link)
- `[PAGE-REF: ...]` → Page relationship (counts as link)
- `[PDF: filename]` → File attachment
- `[~username]` → User mention
- `[MACRO: name ...]` → Unknown macro

### Standard Markdown
- ` ```language\ncode``` ` → Code block
- `| cell | cell |` → Table
- `- [ ]` / `- [x]` → Checkboxes
- `![alt](src)` → Image
- `[text](url)` → Link

### HTML Preserved
- `<details>` → Expandable sections
- `<!-- TOC omitted -->` → TOC placeholder

---

## 🎯 Design Principles

1. **Preserve Meaningful Content**: Convert to placeholders rather than discarding
2. **Skip UI Elements**: Only skip pure decoration (info/note/tip/warning/success/error boxes)
3. **Handle Quirks**: Don't leak status text into expand titles; handle colspan/rowspan correctly
4. **Defensive Parsing**: Fallbacks for everything; never crash
5. **Readable Output**: Clear placeholder formats; consistent syntax

---

## 🐛 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `[MACRO: unknown]` appears | Custom/unrecognized macro | Generic placeholder preserves content |
| Table rendering issues | Complex colspan or nested macros | Colspan expanded; macros processed first |
| Missing user mentions | Non-standard format | Falls back to link text |
| Excessive blank lines | Nested block elements | Post-processing collapses to max 2 newlines |

---

## 📈 Conversion Statistics

- **Macros**: 12 specific + 1 generic fallback
- **HTML Elements**: 20+ standard elements
- **Confluence Elements**: 8 special tags
- **Skipped**: 6 UI macros + 3 element types

### Coverage

**Macros**: 5 content + 6 reference + 1 navigation + 6 UI (skipped)  
**HTML**: 9 block + 7 inline elements  
**Confluence**: macros, parameters, bodies, links, images, emoticons, tasks, attachments, dates

---

## 🔗 Configuration

```python
DEFAULT_CONFLUENCE_DATA_PATH = "/path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 7193
_UI_MACROS = {"info", "note", "tip", "warning", "success", "error"}
```

---

## 📚 Related Files

- **[Main README](../../README.md)** - Project overview
- **[Pipeline README](README.md)** - Full pipeline documentation
- **[check_markdown.py](check_markdown.py)** - Next stage: markdown analysis

---

**Last Updated**: November 20, 2025  
**Version**: 3.0 - Comprehensive Confluence element conversion
