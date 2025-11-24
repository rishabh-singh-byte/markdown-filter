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
- ✅ 31 Confluence macros + generic fallback
- ✅ Smart tables (colspan, dates, macros in cells)
- ✅ Defensive (never crashes, always returns output)
- ✅ Analysis-ready output (links, mentions, files tracked)

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
- **Navigation** → toc, table-of-contents (→ `<!-- TOC omitted -->`)
- **Non-Content** → script, style, ac:placeholder

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

### Complete Macro Reference (31 Types)

| Macro Name | Type | Markdown Output | Analysis |
|------------|------|----------------|----------|
| **code**, **code-block** | Content | ` ```language\ncode``` ` | Words |
| **expand**, **details** | Content | `<details><summary>title</summary>body</details>` | Words |
| **status** | Content | `[STATUS: title]` | Words |
| **panel** | Content | `> **Panel (color):**\n> content` | Words |
| **task-list**, **tasklist** | Content | `- [x]` / `- [ ]` | Words |
| **jira**, **jira-issues**, **jira-issue** | Reference | `[JIRA-REF: ...]` or `N issues [JIRA: ...]` | **Link** |
| **include**, **include-page**, **excerpt-include**, **excerpt** | Reference | `[INCLUDE-REF: page (Space)]` | **Link** |
| **children** | Reference | `[PAGE-REF: Child pages list]` | **Link** |
| **content-by-label** | Reference | `[PAGE-REF: Pages with labels - X]` | **Link** |
| **index** | Reference | `[PAGE-REF: Page index]` | **Link** |
| **viewpdf**, **view-file**, **viewfile** | File | `[PDF: file]` / `[Attachment: file]` | **File** |
| **roadmap**, **roadmap-planner** | Complex | `[MACRO: Roadmap Planner ...]` | Words |
| **toc**, **table-of-contents** | Navigation | `<!-- TOC omitted -->` | *(skipped)* |
| **info**, **note**, **tip**, **warning**, **success**, **error** | UI Only | *(content extracted, box removed)* | *(skipped)* |
| **[unknown]** | Generic | `[MACRO: name (params) -> body]` | Words |

**Categories:**
- Content (8): User-created content → full markdown
- Reference (11): Links to other content → placeholder with details
- File (3): Attachments → file references
- Complex (2): Advanced features → generic placeholder
- Navigation (2): Auto-generated → comment
- UI (6): Styling only → content kept, box removed
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
| `<ac:link>` + `<ri:user>` | `[~username]` | User mentions |
| `<ac:image>` + `<ri:attachment>` | `![caption](filename)` | Attachment images |
| `<ac:emoticon>` | Unicode emoji | ✅ 📋 💭 ⭐ ⚠️ ℹ️ |
| `<ac:task>` + `<ac:task-status>` | `- [x]` / `- [ ]` | Task checkboxes |
| `<time datetime="">` | Formatted date | Auto-detected |
| `<ac:placeholder>` | *(skipped)* | Editor hints |

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
2. Extract parameters → {key: value}
3. Extract body (rich-text → plain-text → fallback)
4. Apply conversion (specific OR generic placeholder)
5. Return markdown
```

### Table Features

- **Header Detection** - Uses `<th>` tags
- **Colspan Expansion** - Adds empty cells for colspan > 1
- **Key-Value Detection** - Special format for 2-column tables
- **Date Auto-Format** - ISO, slash, dash, text formats
- **Macro Support** - Processes macros in cells first
- **Caption** - `<caption>` → bold text above table

### Whitespace Cleaning

- Replace `\xa0` → space, remove `\u200b`
- Unescape HTML entities (`&nbsp;`, `&lt;`)
- Collapse 3+ newlines → max 2
- Remove trailing spaces (except before `|` in tables)

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

---

## ⚙️ Configuration

```python
DEFAULT_CONFLUENCE_DATA_PATH = "/path/to/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 7193
_UI_MACROS = {"info", "note", "tip", "warning", "success", "error"}
```

**Add New Macro Support:**
1. Add case to `_convert_confluence_macro()` function
2. Extract parameters and body
3. Return markdown format
4. Document in this README

---

## 📊 Statistics

| Category | Count |
|----------|-------|
| **Confluence Macros** | 31 (8 content + 11 reference + 3 file + 2 complex + 2 navigation + 6 UI + 1 generic) |
| **HTML Elements** | 20+ (h1-h6, p, div, ul, ol, table, a, img, strong, em, pre, code) |
| **Confluence Tags** | 8 (ac:link, ac:image, ac:emoticon, ac:task, ac:parameter, ac:placeholder) |
| **Actively Converted** | 25 types (22 macros + HTML + Confluence tags) |
| **Skipped** | 8 types (6 UI boxes + 2 navigation + script/style) |

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
