# Confluence HTML to Markdown Converter (conversion3.py)

**Purpose**: Convert Confluence Storage Format (XHTML) to clean, readable Markdown while preserving all meaningful content.

**Core Function**: `convert_html_to_markdown(html_str: str) -> str`

---

## 📋 What Are Confluence Macros?

**Confluence Macros** are special UI components in Confluence pages that provide rich functionality beyond standard HTML. They appear in the Confluence Storage Format (the raw HTML stored in the database) as special XML-like tags.

**Example of a Confluence Macro in Storage Format**:
```xml
<ac:structured-macro ac:name="code" ac:schema-version="1">
    <ac:parameter ac:name="language">python</ac:parameter>
    <ac:plain-text-body><![CDATA[def hello():
    print("Hello World")]]></ac:plain-text-body>
</ac:structured-macro>
```

**What This Looks Like in Markdown**:
```python
def hello():
    print("Hello World")
```

---

## 🔄 Conversion Overview

```
Confluence XHTML Input
         ↓
Parse with BeautifulSoup
         ↓
Identify macros, tables, lists, etc.
         ↓
Convert each element to Markdown
         ↓
Clean whitespace & format
         ↓
Output: Clean Markdown
```

---

## 📦 Macro Categories

### 1. **Content Macros** (Converted to Markdown equivalents)
Macros that contain actual content worth preserving.

### 2. **Reference Macros** (Converted to placeholder text)
Macros that reference other content but don't contain direct content.

### 3. **UI Macros** (Skipped entirely)
Macros that are purely decorative or provide UI hints.

---

## 🎯 Supported Macros & Conversion Logic

### 1. Code Macro
**Confluence Macro**: `code`, `code-block`

**What It Does**: Displays formatted code snippets with syntax highlighting.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="code">
    <ac:parameter ac:name="language">javascript</ac:parameter>
    <ac:plain-text-body>
        function greet(name) {
            return `Hello, ${name}!`;
        }
    </ac:plain-text-body>
</ac:structured-macro>
```

**Markdown Output**:
````markdown
```javascript
function greet(name) {
    return `Hello, ${name}!`;
}
```
````

**How It's Handled**:
- Extracts `language` parameter for syntax highlighting hint
- Extracts code from `<ac:plain-text-body>` or `<pre>` tags
- Wraps in Markdown code fence with language specifier

---

### 2. Expand Macro
**Confluence Macro**: `expand`, `details`

**What It Does**: Creates collapsible sections that users can expand/collapse.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="expand">
    <ac:parameter ac:name="title">Click to expand details</ac:parameter>
    <ac:rich-text-body>
        <p>This content is hidden until clicked.</p>
    </ac:rich-text-body>
</ac:structured-macro>
```

**Markdown Output**:
```markdown
<details>
<summary>Click to expand details</summary>

This content is hidden until clicked.

</details>
```

**How It's Handled**:
- Extracts `title` or `label` parameter for summary text
- Recursively converts inner content to Markdown
- Wraps in HTML `<details>` tag (supported by Markdown parsers)
- **Important**: Does NOT use body text as title to avoid leaking status macro text like "DRAFT"

---

### 3. Status Macro
**Confluence Macro**: `status`

**What It Does**: Displays colored status badges (e.g., "IN PROGRESS", "DRAFT", "APPROVED").

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="status">
    <ac:parameter ac:name="title">DRAFT</ac:parameter>
    <ac:parameter ac:name="colour">Yellow</ac:parameter>
</ac:structured-macro>
```

**Markdown Output**:
```
[STATUS: DRAFT]
```

**How It's Handled**:
- Extracts `title` parameter as status text
- Extracts `colour`/`color` parameter (currently not used in output)
- Formats as readable placeholder: `[STATUS: title]`

---

### 4. Table of Contents Macro
**Confluence Macro**: `toc`, `table-of-contents`

**What It Does**: Auto-generates a table of contents from page headings.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="toc">
    <ac:parameter ac:name="maxLevel">3</ac:parameter>
</ac:structured-macro>
```

**Markdown Output**:
```html
<!-- TOC omitted: Table of Contents macro -->
```

**How It's Handled**:
- Replaced with HTML comment placeholder
- Cannot be accurately reproduced in Markdown (dynamic content)
- Indicates presence of navigation structure

---

### 5. File/PDF Viewer Macros
**Confluence Macro**: `viewpdf`, `view-file`, `viewfile`

**What It Does**: Embeds PDF or file viewers directly in the page.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="viewpdf">
    <ac:parameter ac:name="name">project-specs.pdf</ac:parameter>
    <ac:default-parameter>
        <ri:attachment ri:filename="project-specs.pdf"/>
    </ac:default-parameter>
</ac:structured-macro>
```

**Markdown Output**:
```
[PDF: project-specs.pdf]
```
or
```
[Attachment: project-specs.pdf]
```

**How It's Handled**:
- Extracts `name` or `file` parameter
- Falls back to parsing `<ri:attachment>` tag for filename
- Formats as file reference placeholder
- Preserves file name for content analysis

---

### 6. Include Macros
**Confluence Macro**: `include`, `include-page`, `excerpt-include`, `excerpt`

**What It Does**: Embeds content from another Confluence page.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="include">
    <ac:parameter ac:name="page">API Documentation</ac:parameter>
    <ac:parameter ac:name="space">DEV</ac:parameter>
</ac:structured-macro>
```

**Markdown Output**:
```
[INCLUDE-REF: API Documentation (Space: DEV)]
```

**How It's Handled**:
- Extracts `page`, `name`, or `pageTitle` parameter
- Extracts `space` or `spaceKey` parameter
- Formats as clear reference indicating cross-page relationship
- Treated as a **link reference** for page quality analysis

---

### 7. Jira Macros
**Confluence Macro**: `jira`, `jira-issues`, `jira-issue`

**What It Does**: Displays Jira issues or issue counts based on JQL queries.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="jira">
    <ac:parameter ac:name="server">System Jira</ac:parameter>
    <ac:parameter ac:name="jqlQuery">project = "MYPROJ" AND status = "In Progress"</ac:parameter>
    <ac:parameter ac:name="count">true</ac:parameter>
</ac:structured-macro>
```

**Markdown Output** (when count=true):
```
N issues [JIRA: MYPROJ]
```

**Markdown Output** (when count=false or missing):
```
[JIRA-REF: System Jira - MYPROJ]
```

**How It's Handled**:
- Extracts `server` or `servername` parameter
- Extracts `jqlQuery` and parses project name using regex
- Checks `count` parameter to determine if it shows count or full list
- Formats differently based on display type:
  - **Count mode**: Shows "N issues" (placeholder for dynamic count)
  - **List mode**: Shows full Jira reference
- Treated as a **link reference** for page quality analysis

---

### 8. Task List Macro
**Confluence Macro**: `task-list`, `tasklist`

**What It Does**: Creates interactive checkbox lists for tasks.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="task-list">
    <ac:rich-text-body>
        <ac:task>
            <ac:task-status>complete</ac:task-status>
            <ac:task-body>Review documentation</ac:task-body>
        </ac:task>
        <ac:task>
            <ac:task-status>incomplete</ac:task-status>
            <ac:task-body>Update API specs</ac:task-body>
        </ac:task>
    </ac:rich-text-body>
</ac:structured-macro>
```

**Markdown Output**:
```markdown
- [x] Review documentation
- [ ] Update API specs
```

**How It's Handled**:
- Parses each `<ac:task>` element
- Checks `<ac:task-status>` for "complete" status
- Extracts `<ac:task-body>` for task text
- Converts to Markdown checkbox list format

---

### 9. Panel Macro
**Confluence Macro**: `panel`

**What It Does**: Creates colored boxes/panels for highlighting content.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="panel">
    <ac:parameter ac:name="bgColor">#E3FCEF</ac:parameter>
    <ac:rich-text-body>
        <p><strong>Important Note:</strong> Remember to update the configuration.</p>
    </ac:rich-text-body>
</ac:structured-macro>
```

**Markdown Output**:
```markdown
> **Panel (#E3FCEF):**
>
> **Important Note:** Remember to update the configuration.
```

**How It's Handled**:
- Extracts `bgColor` or `color` parameter
- Recursively converts inner content to Markdown
- Wraps in Markdown blockquote (`>`) to indicate special section
- Preserves nested block structure (paragraphs, lists, tables)

---

### 10. Navigation/Reference Macros
**Confluence Macros**: `index`, `content-by-label`, `children`

**What They Do**: Display lists of related pages with links.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="children">
    <ac:parameter ac:name="all">true</ac:parameter>
</ac:structured-macro>
```

**Markdown Output**:
```
[PAGE-REF: Child pages list]
```
or
```
[PAGE-REF: Pages with labels - api,documentation]
```
or
```
[PAGE-REF: Page index]
```

**How It's Handled**:
- **children**: Lists child pages → `[PAGE-REF: Child pages list]`
- **content-by-label**: Pages with specific labels → `[PAGE-REF: Pages with labels - {labels}]`
- **index**: Page index/TOC → `[PAGE-REF: Page index]`
- **Important**: These are treated as **link references** in quality analysis
- They indicate page relationships and navigation structure

---

### 11. Roadmap Macro
**Confluence Macro**: `roadmap`, `roadmap-planner`

**What It Does**: Displays project roadmaps and planning timelines.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="roadmap-planner">
    <ac:parameter ac:name="title">Q4 2024 Roadmap</ac:parameter>
    <ac:parameter ac:name="timelineStart">2024-10-01</ac:parameter>
    <ac:parameter ac:name="timelineEnd">2024-12-31</ac:parameter>
</ac:structured-macro>
```

**Markdown Output**:
```
[MACRO: Q4 2024 Roadmap (timelineStart=2024-10-01, timelineEnd=2024-12-31)]
```

**How It's Handled**:
- Extracts `title` or `label` parameter
- Extracts all parameters (filters out long encoded values)
- Formats as generic macro placeholder with parameters
- Useful for indicating presence of complex planning content

---

### 12. UI Macros (Skipped)
**Confluence Macros**: `info`, `note`, `tip`, `warning`, `success`, `error`

**What They Do**: Display colored information boxes for user notifications.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="info">
    <ac:rich-text-body>
        <p>This is an informational message.</p>
    </ac:rich-text-body>
</ac:structured-macro>
```

**Markdown Output**:
```
(nothing - completely skipped)
```

**How It's Handled**:
- These macros are **completely skipped** during conversion
- **Reason**: They're purely decorative UI elements
- Content analysis focuses on actual information, not presentation
- Prevents false positives in word count and content detection

---

### 13. Unknown/Generic Macros
**Any Macro Not Explicitly Handled**

**What It Does**: Fallback handler for custom or uncommon macros.

**Storage Format Example**:
```xml
<ac:structured-macro ac:name="custom-widget">
    <ac:parameter ac:name="setting">value123</ac:parameter>
    <ac:rich-text-body>
        <p>Some content here</p>
    </ac:rich-text-body>
</ac:structured-macro>
```

**Markdown Output**:
```
[MACRO: custom-widget setting=value123 -> Some content here]
```

**How It's Handled**:
- Extracts macro name
- Extracts all parameters as key=value pairs
- Extracts body text as preview
- Formats as: `[MACRO: name params -> preview]`
- **Important**: This ensures no macro content is lost, even if not explicitly supported

---

## 🎨 Special Elements Handling

### Placeholders (Skipped)
**Confluence Element**: `<ac:placeholder>`

**What It Does**: Editor hints shown in Confluence edit mode (not visible to readers).

**Storage Format Example**:
```xml
<ac:placeholder>Type your content here...</ac:placeholder>
```

**Markdown Output**:
```
(nothing - completely skipped)
```

**How It's Handled**:
- **Completely ignored** during conversion
- **Reason**: These are UI hints for editors, never visible to readers
- Not actual content, should not be counted in analysis
- Common in empty cells and unfilled templates

---

### User Mentions
**Confluence Element**: `<ac:link>` with `<ri:user>`

**What It Does**: References/mentions Confluence users.

**Storage Format Example**:
```xml
<ac:link>
    <ri:user ri:account-id="557058:12345-6789"/>
</ac:link>
```

**Markdown Output**:
```
[~557058:12345-6789]
```

**How It's Handled**:
- Extracts `ri:account-id`, `username`, or `ri:username` attribute
- Formats as `[~username]` (Confluence mention syntax)
- Multiple users in one link are comma-separated
- Treated as **user mentions** in content analysis

---

### Emoticons
**Confluence Element**: `<ac:emoticon>`

**What It Does**: Displays emoji icons.

**Storage Format Example**:
```xml
<ac:emoticon ac:name="white_check_mark"/>
```

**Markdown Output**:
```
✅
```

**How It's Handled**:
- Maps common emoji names to Unicode characters
- Supported emojis: clipboard 📋, thought balloon 💭, check marks ✅, star ⭐, warning ⚠️, info ℹ️
- Falls back to `:emoji_name:` format for unknown emojis

---

### Images
**Confluence Elements**: `<img>`, `<ac:image>`

**What They Do**: Display embedded images.

**Storage Format Example**:
```xml
<ac:image>
    <ri:attachment ri:filename="architecture-diagram.png"/>
    <ac:plain-text-body>System Architecture</ac:plain-text-body>
</ac:image>
```

**Markdown Output**:
```markdown
![System Architecture](architecture-diagram.png)
```

**How It's Handled**:
- For `<img>`: Extracts `src` and `alt` attributes
- For `<ac:image>`: Extracts filename from `<ri:attachment>` and caption from `<ac:plain-text-body>`
- Converts to Markdown image syntax: `![alt](src)`
- Treated as **image content** in quality analysis

---

### Tables
**Confluence Element**: `<table>`

**What It Does**: Standard HTML tables with Confluence enhancements.

**Special Handling**:

#### Regular Tables
```html
<table>
    <tr>
        <th>Name</th>
        <th>Status</th>
    </tr>
    <tr>
        <td>Project A</td>
        <td>Active</td>
    </tr>
</table>
```

**Markdown Output**:
```markdown
| Name | Status |
| --- | --- |
| Project A | Active |
```

#### Key-Value Tables (2 columns)
```html
<table>
    <tr>
        <th>Property</th>
        <td>Value</td>
    </tr>
    <tr>
        <th>Database</th>
        <td>PostgreSQL</td>
    </tr>
</table>
```

**Markdown Output**:
```markdown
| Property | Value |
| --- | --- |
| Database | PostgreSQL |
```

**Advanced Features**:
1. **Colspan handling**: Cells with `colspan="2"` are expanded into multiple empty cells
2. **Header detection**: Uses `<th>` tags to identify header rows
3. **Caption support**: `<caption>` becomes bold text above table
4. **Date extraction**: Recognizes and formats date patterns in cells
5. **Macro processing**: Processes macros within table cells before conversion

---

### Lists
**Confluence Elements**: `<ul>`, `<ol>`, `<li>`

**What They Do**: Unordered (bullet) and ordered (numbered) lists.

**Storage Format Example**:
```html
<ul>
    <li>First item</li>
    <li>Second item
        <ul>
            <li>Nested item</li>
        </ul>
    </li>
</ul>
```

**Markdown Output**:
```markdown
- First item
- Second item
  - Nested item
```

**How It's Handled**:
- Supports unlimited nesting with proper indentation (2 spaces per level)
- Ordered lists use `1.`, `2.`, etc.
- Unordered lists use `-`
- Preserves nested structure

---

### Headings
**Confluence Elements**: `<h1>`, `<h2>`, `<h3>`, `<h4>`, `<h5>`, `<h6>`

**Markdown Output**:
```markdown
# Heading 1
## Heading 2
### Heading 3
```

**How It's Handled**:
- Converts directly to Markdown heading syntax
- Preserves heading level (1-6)

---

### Links
**Confluence Element**: `<a>`

**Storage Format Example**:
```html
<a href="https://example.com">Visit Example</a>
<a href="mailto:team@example.com">Email Us</a>
```

**Markdown Output**:
```markdown
[Visit Example](https://example.com)
[Email Us](mailto:team@example.com)
```

**How It's Handled**:
- Extracts `href` attribute as URL
- Extracts link text
- Preserves mailto: links
- Treated as **links** in content analysis

---

## 🧹 Whitespace & Formatting Rules

### 1. **Whitespace Cleaning**
```python
_clean_whitespace(text, keep_newlines=False)
```
- Removes non-breaking spaces (`\xa0`) and zero-width spaces (`\u200b`)
- Unescapes HTML entities
- When `keep_newlines=True`: Preserves line breaks (for tables/code)
- When `keep_newlines=False`: Collapses all whitespace to single spaces

### 2. **Pipe Escaping**
```python
_escape_pipe(text)
```
- Escapes `|` characters as `\|` in table cells
- Prevents breaking Markdown table structure

### 3. **Post-Processing**
After conversion:
- Collapse 3+ consecutive newlines to maximum 2
- Remove trailing spaces before newlines (except in tables)
- Ensure document ends with single newline

---

## 📦 Macro Processing Details

### How Macros Are Parsed

**Step 1: Macro Identification**
```python
<ac:structured-macro ac:name="code">  # OR <ac:macro ac:name="code">
```
- Both `ac:structured-macro` and `ac:macro` are recognized
- Macro name extracted from `ac:name`, `name`, or `ac:macro-name` attribute

**Step 2: Parameter Extraction**
```xml
<ac:parameter ac:name="language">python</ac:parameter>
<ac:parameter ac:name="title">My Code</ac:parameter>
```
- All `<ac:parameter>` tags extracted into dictionary
- Key = `ac:name` attribute value
- Value = text content inside parameter tag

**Step 3: Metadata Extraction**
```xml
<ac:structured-macro ac:macro-id="abc123" ac:schema-version="1">
```
- Attributes like `ac:macro-id`, `ac:schema-version` stored as metadata
- Used in fallback rendering for unknown macros
- Helps with debugging and tracking macro versions

**Step 4: Body Extraction**
Three types of body content:
1. **Rich Text Body**: `<ac:rich-text-body>` - Contains nested HTML, recursively converted
2. **Plain Text Body**: `<ac:plain-text-body>` - Plain text, directly extracted
3. **Default**: If neither present, extracts all inner content

**Step 5: Rendering**
- Known macros → Specific conversion logic
- Unknown macros → Generic placeholder with parameters and body preview

---

## 🔍 Date Detection in Tables

**What It Does**: Automatically recognizes and formats dates in table cells.

**Supported Date Formats**:
1. ISO format: `2023-01-15`
2. Slash format: `2023/01/15` or `01/15/2023`
3. Dash format: `01-15-2023`
4. Text format: `Jan 15, 2023` or `15 Jan 2023`

**Special Handling**:
- Checks for Confluence `<time>` element first
- Parses `datetime` attribute (ISO format)
- Falls back to text content
- Uses regex patterns for common date formats

---

## ⚙️ Configuration

```python
# Data file for testing
DEFAULT_CONFLUENCE_DATA_PATH = "/path/to/confluence_markdown.jsonl"

# Test record index
DEFAULT_TEST_INDEX = 7193

# UI macros to skip (not useful for content analysis)
_UI_MACROS = {"info", "note", "tip", "warning", "success", "error"}
```

---

## 🚀 Usage

### Basic Usage
```python
from filter.main.conversion3 import convert_html_to_markdown

# Confluence HTML input
html = """
<ac:structured-macro ac:name="code">
    <ac:parameter ac:name="language">python</ac:parameter>
    <ac:plain-text-body>print("Hello")</ac:plain-text-body>
</ac:structured-macro>
"""

# Convert to Markdown
markdown = convert_html_to_markdown(html)
print(markdown)
# Output: ```python
#         print("Hello")
#         ```
```

### Testing with Confluence Data
```bash
# Test with default index
python conversion3.py

# Edit DEFAULT_TEST_INDEX in file to test different records
```

**Output**: Shows both original HTML and converted Markdown side-by-side.

---

## 🎯 Design Principles

### 1. **Preserve All Meaningful Content**
- Never discard information that could be useful
- Convert macros to readable placeholders rather than omitting
- Keep reference information (includes, jira, page refs)

### 2. **Skip Only Pure UI Elements**
- Only skip macros that are purely decorative (`info`, `note`, etc.)
- These don't contribute to page quality analysis

### 3. **Handle Confluence Quirks**
- Don't leak status macro text (like "DRAFT") into expand titles
- Handle colspan/rowspan properly in tables
- Recognize key-value tables vs regular tables

### 4. **Defensive Parsing**
- Use try/except for date parsing
- Fall back to text content when structured data missing
- Handle missing attributes gracefully

### 5. **Readable Output**
- Use clear placeholder formats: `[MACRO: name]`, `[STATUS: text]`
- Format user mentions consistently: `[~username]`
- Keep nested structures (lists, blockquotes)

---

## 📊 Content Preserved for Analysis

The conversion preserves these elements for downstream quality analysis:

| Element | Markdown Format | Analysis Category |
|---------|----------------|-------------------|
| Links (`<a>`) | `[text](url)` | **Links** |
| Images | `![alt](src)` | **Images** |
| File attachments | `[PDF: name]` | **Files** |
| User mentions | `[~username]` | **Mentions** |
| Include macros | `[INCLUDE-REF: page]` | **Links** |
| Jira macros | `[JIRA-REF: ...]` | **Links** |
| Children/index macros | `[PAGE-REF: ...]` | **Links** |
| Status macros | `[STATUS: text]` | **Words** |
| Task lists | `- [x] task` | **Words** |
| Code blocks | ` ```code``` ` | **Words** |
| Tables | Markdown tables | **Tables** |
| Regular text | Plain text | **Words** |

---

## 🧪 Example Conversions

### Example 1: Complex Page with Multiple Macros

**Input HTML**:
```xml
<h1>API Documentation</h1>
<p>Last updated by <ac:link><ri:user ri:account-id="john.doe"/></ac:link></p>

<ac:structured-macro ac:name="status">
    <ac:parameter ac:name="title">DRAFT</ac:parameter>
    <ac:parameter ac:name="colour">Yellow</ac:parameter>
</ac:structured-macro>

<ac:structured-macro ac:name="toc"/>

<h2>Overview</h2>
<p>This API provides access to user data.</p>

<ac:structured-macro ac:name="code">
    <ac:parameter ac:name="language">bash</ac:parameter>
    <ac:plain-text-body>curl -X GET https://api.example.com/users</ac:plain-text-body>
</ac:structured-macro>

<ac:structured-macro ac:name="jira">
    <ac:parameter ac:name="server">System Jira</ac:parameter>
    <ac:parameter ac:name="jqlQuery">project = "API"</ac:parameter>
</ac:structured-macro>
```

**Output Markdown**:
```markdown
# API Documentation

Last updated by [~john.doe]

[STATUS: DRAFT]

<!-- TOC omitted: Table of Contents macro -->

## Overview

This API provides access to user data.

```bash
curl -X GET https://api.example.com/users
```

[JIRA-REF: System Jira - API]
```

---

### Example 2: Table with Macros and Dates

**Input HTML**:
```xml
<table>
    <tr>
        <th>Task</th>
        <th>Status</th>
        <th>Due Date</th>
    </tr>
    <tr>
        <td>Update API</td>
        <td>
            <ac:structured-macro ac:name="status">
                <ac:parameter ac:name="title">In Progress</ac:parameter>
            </ac:structured-macro>
        </td>
        <td><time datetime="2024-12-31">Dec 31, 2024</time></td>
    </tr>
</table>
```

**Output Markdown**:
```markdown
| Task | Status | Due Date |
| --- | --- | --- |
| Update API | [STATUS: In Progress] | 2024-12-31 |
```

---

## 🔗 Related Documentation

- **[Main README](../../README.md)** - Project overview
- **[Pipeline README](README.md)** - Complete pipeline documentation
- **[check_markdown.py](check_markdown.py)** - Next stage: markdown analysis

---

## 🐛 Common Issues & Solutions

### Issue: Macros Appearing as `[MACRO: unknown]`

**Cause**: Unknown or custom macro not explicitly handled.

**Solution**: The macro is converted to a generic placeholder with parameters. This preserves macro presence for analysis.

---

### Issue: Tables Not Rendering Correctly

**Cause**: Complex colspan/rowspan or nested macros in cells.

**Solution**: 
- Colspan is expanded to empty cells
- Macros in cells are processed first
- Tables are normalized to equal column counts

---

### Issue: User Mentions Not Showing

**Cause**: Non-standard user mention format.

**Solution**: Falls back to link text if `ri:account-id` not found.

---

### Issue: Excessive Blank Lines

**Cause**: Multiple consecutive block elements.

**Solution**: Post-processing collapses 3+ newlines to 2 maximum.

---

## 📝 Complete Macro Reference

### Content Macros (Converted)
| Macro | Output | Use Case |
|-------|--------|----------|
| `code` / `code-block` | ` ```language\ncode\n``` ` | Code snippets |
| `expand` / `details` | `<details><summary>...</summary></details>` | Collapsible sections |
| `status` | `[STATUS: title]` | Status badges |
| `task-list` / `tasklist` | `- [x] task` | Checkbox lists |
| `panel` | `> **Panel:**...` | Highlighted boxes |

### Reference Macros (Placeholders)
| Macro | Output | Treated As |
|-------|--------|-----------|
| `include` / `include-page` | `[INCLUDE-REF: page]` | **Link** |
| `excerpt-include` / `excerpt` | `[INCLUDE-REF: page]` | **Link** |
| `jira` / `jira-issues` | `[JIRA-REF: ...]` | **Link** |
| `children` | `[PAGE-REF: Child pages]` | **Link** |
| `content-by-label` | `[PAGE-REF: Pages with labels]` | **Link** |
| `index` | `[PAGE-REF: Page index]` | **Link** |
| `viewpdf` / `view-file` | `[PDF: filename]` | **File** |
| `roadmap` / `roadmap-planner` | `[MACRO: Roadmap ...]` | **Content** |

### Navigation Macros (Placeholders)
| Macro | Output | Purpose |
|-------|--------|---------|
| `toc` / `table-of-contents` | `<!-- TOC omitted -->` | Auto-generated TOC |

### Skipped Macros (No Output)
| Macro | Reason |
|-------|--------|
| `info`, `note`, `tip`, `warning`, `success`, `error` | Pure UI decoration |
| `ac:placeholder` | Editor hints only |

### Unknown Macros (Generic Handler)
| Input | Output |
|-------|--------|
| Any unrecognized macro | `[MACRO: name params -> preview]` |

---

## 🔑 Key Takeaways

### What Gets Preserved
✅ **All meaningful content**: Code, text, status, tasks  
✅ **All references**: Links, includes, Jira issues, page relationships  
✅ **All file attachments**: PDFs, images, documents  
✅ **All user mentions**: @username references  
✅ **All tables**: With proper formatting and macro content  

### What Gets Skipped
❌ **UI decoration**: Info boxes, note boxes, warning boxes  
❌ **Editor hints**: Placeholders visible only in edit mode  
❌ **Empty metadata**: Style tags, script tags  

### Why This Matters
- **Page Quality Analysis**: Distinguishes real content from decoration
- **Word Counting**: Only counts meaningful words, not UI text
- **Link Detection**: Recognizes all types of cross-page references
- **Content Preservation**: No information loss, even for unknown macros

---

**Module**: conversion3.py  
**Macros Supported**: 13+ macro types (12 specific + generic handler)  
**Special Elements**: Tables, Lists, Images, Links, User Mentions, File References, Emoticons  
**Skipped Elements**: 7 UI macros + placeholders  

---

**Last Updated**: November 17, 2025  
**Coverage**: Complete macro documentation
