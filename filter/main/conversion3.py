#!/usr/bin/env python3
"""
Confluence XHTML to Markdown Converter
=======================================
Robust converter for Confluence Storage Format (XHTML) to Markdown.

Public API:
    convert_html_to_markdown(html_str: str) -> str

Features:
- Preserves visible content (placeholders, status titles, macro parameters)
- Handles tables robustly: expands colspan & rowspan, preserves <th> positions
- UI-heavy macros (roadmap, jira, etc.) are emitted as compact placeholders
- Defensive parsing and whitespace cleaning
"""

# =============================================================================
#                           IMPORTS
# =============================================================================

from bs4 import BeautifulSoup, Tag, NavigableString, FeatureNotFound
import re
import html
import json
import sys
from typing import Tuple, Dict, Any, List, Optional

# =============================================================================
#                           CONFIGURATION CONSTANTS
# =============================================================================

# UI Macros - Not useful for page analysis
_UI_MACROS = {"info", "note", "tip", "warning", "success", "error"}

# Default input file path for testing
DEFAULT_CONFLUENCE_DATA_PATH = "/Users/rishabh.singh/Desktop/markdown_filter/filter/data/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 1154


# =============================================================================
#                           UTILITY FUNCTIONS
# =============================================================================

def _clean_whitespace(s: Optional[str], keep_newlines: bool = False) -> str:
    if not s:
        return ""
    s = s.replace('\xa0', ' ').replace('\u200b', '')
    s = html.unescape(s)
    if keep_newlines:
        # Preserve structure for tables and Markdown blocks
        s = re.sub(r'[ \t]+', ' ', s)
        # Prevent accidental flattening: collapse multiple blank lines but keep single newlines
        s = re.sub(r'\n{3,}', '\n\n', s)
        return s.strip()
    return re.sub(r'\s+', ' ', s).strip()

def _escape_pipe(s: str) -> str:
    """Escape pipe characters for Markdown table cells."""
    return s.replace('|', '\\|')

def _extract_and_format_date(cell: Tag) -> Optional[str]:
    """
    Extract and format date from table cell, handling Confluence time elements and common date formats.
    Returns formatted date string or None if no date found.
    """
    # Check for Confluence <time> element first
    time_elem = cell.find('time')
    if time_elem:
        # Try datetime attribute (ISO format)
        dt = time_elem.get('datetime')
        if dt:
            # Parse ISO format and return readable format
            try:
                from datetime import datetime
                parsed = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                return parsed.strftime('%Y-%m-%d')
            except (ValueError, AttributeError):
                pass
        # Fall back to visible text in time element
        time_text = _clean_whitespace(time_elem.get_text())
        if time_text:
            return time_text
    
    # Check for common date patterns in cell text
    cell_text = _clean_whitespace(cell.get_text())
    if not cell_text:
        return None
    
    # Common date patterns
    date_patterns = [
        (r'\d{4}-\d{2}-\d{2}', None),  # ISO: 2023-01-15
        (r'\d{4}/\d{2}/\d{2}', None),  # 2023/01/15
        (r'\d{1,2}/\d{1,2}/\d{4}', None),  # 01/15/2023 or 1/15/2023
        (r'\d{1,2}-\d{1,2}-\d{4}', None),  # 01-15-2023
        (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}', None),  # Jan 15, 2023
        (r'\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}', None),  # 15 Jan 2023
    ]
    
    for pattern, _ in date_patterns:
        match = re.search(pattern, cell_text, re.IGNORECASE)
        if match:
            return match.group(0)
    
    return None

# =============================================================================
#                           MACRO HELPER FUNCTIONS
# =============================================================================

def _extract_macro_params(macro_tag: Tag) -> Dict[str, str]:
    """Extract <ac:parameter ac:name="...">value</ac:parameter> into dict."""
    params = {}
    for p in macro_tag.find_all('ac:parameter'):
        name = p.get('ac:name') or p.get('name') or ''
        text = _clean_whitespace(p.get_text(" ", strip=True))
        if name:
            params[name] = text
    return params

def _extract_macro_metadata(macro_tag: Tag) -> Dict[str, str]:
    """Extract metadata attributes from macro tag (ac:macro-id, ac:schema-version, etc.)"""
    metadata = {}
    for attr, val in macro_tag.attrs.items():
        if attr.startswith("ac:") and attr not in ("ac:name", "ac:macro-name"):
            metadata[attr] = str(val)
    return metadata


def _extract_macro_body(macro_tag: Tag) -> str:
    """Extract rich text body if present."""
    # ac:rich-text-body may contain nested HTML we want to convert recursively
    body = macro_tag.find('ac:rich-text-body')
    if body:
        return ''.join(str(c) for c in body.contents)

    # fallback to plain text body
    pt = macro_tag.find('ac:plain-text-body')
    if pt:
        return _clean_whitespace(pt.get_text(" ", strip=True))
    # otherwise return inner HTML
    return ''.join(str(c) for c in macro_tag.contents)

def _users_from_ac_link(ac_link: Tag) -> List[str]:
    """Extract users from <ac:link> containing <ri:user> tags, fallback to inner text."""
    users = []
    for u in ac_link.find_all('ri:user'):
        # try common attributes
        acct = u.get('ri:account-id') or u.get('username') or u.get('ri:username') or u.get('acct')
        if acct:
            users.append(acct)
        else:
            # maybe inner display
            text = _clean_whitespace(u.get_text(" ", strip=True))
            if text:
                users.append(text)
    # If no ri:user children, fallback to link text
    if not users:
        text = _clean_whitespace(ac_link.get_text(" ", strip=True))
        if text:
            users.append(text)
    # Format as @user:id for readability
    return [f"[~{u.replace('@','')}]" for u in users]

# =============================================================================
#                           NODE TO MARKDOWN CONVERSION
# =============================================================================

def _node_to_markdown(node, list_level: int = 0) -> str:
    """Convert a BeautifulSoup node or subtree into Markdown text."""
    if node is None:
        return ""
    if isinstance(node, NavigableString):
        return _clean_whitespace(str(node))
    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()

    # Skip style/script
    if name in ('script', 'style'):
        return ""

    # Skip ac:placeholder - these are editor hints, not visible content
    if name == 'ac:placeholder':
        return ""
    
    # Skip span.text-placeholder - these are instructional placeholder text
    if name == 'span':
        classes = node.get('class', [])
        # Filter out all types of placeholder spans
        if 'text-placeholder' in classes or 'placeholder-inline-tasks' in classes:
            return ""

    # Handle ac:task-list and ac:task tags (when inside table cells or other elements)
    if name == 'ac:task-list':
        tasks_md = []
        for task in node.find_all('ac:task'):
            status = task.find('ac:task-status')
            body = task.find('ac:task-body')
            
            # Check if body only contains placeholder
            if body:
                # Remove placeholder elements before getting text
                body_copy = BeautifulSoup(str(body), "html.parser")
                for placeholder in body_copy.find_all('ac:placeholder'):
                    placeholder.decompose()
                text = _clean_whitespace(body_copy.get_text(" ", strip=True))
            else:
                text = ''
            
            # Skip empty tasks (no real content, only placeholders)
            if not text:
                continue
            
            checked = (status and status.get_text(strip=True).lower() == 'complete')
            checkbox = "[x]" if checked else "[ ]"
            tasks_md.append(f"- {checkbox} {text}")
        
        return "\n".join(tasks_md) + "\n" if tasks_md else ""
    
    # Handle ac:adf-extension tags (decision lists, etc.)
    if name == 'ac:adf-extension':
        # ADF extensions are placeholder content for decision lists, etc.
        # Check if there's real content (not just placeholders)
        content_copy = BeautifulSoup(str(node), "html.parser")
        for placeholder in content_copy.find_all('ac:placeholder'):
            placeholder.decompose()
        # Remove ADF metadata attributes (local-id, state, etc.)
        for adf_attr in content_copy.find_all('ac:adf-attribute'):
            adf_attr.decompose()
        text = _clean_whitespace(content_copy.get_text(" ", strip=True))
        # If only placeholders, return empty
        return "" if not text else f"[ADF-CONTENT: {text[:50]}...]"

    # Handle structured macros and ac:macro directly
    if name in ('ac:structured-macro', 'ac:macro'):
        macro_name = node.get('ac:name') or node.get('name') or node.get('ac:macro-name') or ''
        params = _extract_macro_params(node)
        metadata = _extract_macro_metadata(node)
        body_html = _extract_macro_body(node)
        return _render_macro(macro_name, params, body_html, metadata=metadata)


    if name == 'ac:emoticon':
        emoji_key = node.get('ac:emoji-shortname') or node.get('ac:name') or ''
        emoji_key = emoji_key.strip(':').replace('-', '_')
        emoji_map = {
            'clipboard': '📋',
            'thought_balloon': '💭',
            'white_check_mark': '✅',
            'blue_star': '⭐',
            'warning': '⚠️',
            'information_source': 'ℹ️',
            'check_mark_button': '✅',
        }
        return emoji_map.get(emoji_key, f":{emoji_key}:")

    # Handle Confluence link to users <ac:link> that wraps <ri:user>
    if name == 'ac:link':
        users = _users_from_ac_link(node)
        # join multiple users as comma-separated
        return ", ".join(users)

    # Images
    if name == 'img':
        src = node.get('src') or node.get('data-src') or ''
        alt = _clean_whitespace(node.get('alt') or '')
        if src:
            return f"![{alt}]({src})"
        else:
            # fallback: just show alt if src missing
            return alt
    
    if name == 'ac:image':
        # Try attachment
        att = node.find('ri:attachment')
        src = att.get('ri:filename') if att else None
        # Try alt/caption
        caption = node.find('ac:plain-text-body')
        alt_text = _clean_whitespace(caption.get_text()) if caption else ''
        if src:
            return f"![{alt_text}]({src})"
        return alt_text or "[Image]"
    
    # Anchors
    if name == 'a':
        href = node.get('href', '').strip()
        text = _clean_whitespace(node.get_text(" ", strip=True))
        if href.startswith('mailto:'):
            return f"[{text}]({href})"
        if href:
            return f"[{text or href}]({href})"
        return text

    # Lists
    if name in ('ul', 'ol'):
        return _list_to_markdown(node, indent=list_level)

    # Headings
    if re.match(r'h[1-6]', name):
        level = int(name[1])
        inner = _clean_whitespace(node.get_text(" ", strip=True))
        return f"\n{'#'*level} {inner}\n\n"

    # Code blocks (native or ac:plain-text-body handled in macros)
    if name == 'pre' or name == 'code':
        txt = node.get_text()
        return f"\n```\n{txt.rstrip()}\n```\n"

    # Tables
    if name == 'table':
        return _table_to_markdown(node)

    # Paragraphs or divs: preserve line breaks between block children
    if name in ('p', 'div', 'section'):
        contents = []
        for child in node.children:
            txt = _node_to_markdown(child, list_level=list_level)
            if txt:
                contents.append(txt)
        joined = " ".join(c for c in contents if c)
        return f"\n{_clean_whitespace(joined)}\n\n" if joined.strip() else ""

    # Inline elements: strong, em, span, b, i
    if name in ('strong', 'b'):
        inner = _clean_whitespace(node.get_text(" ", strip=True))
        return f"**{inner}**"
    if name in ('em', 'i'):
        inner = _clean_whitespace(node.get_text(" ", strip=True))
        return f"*{inner}*"

    # Default: recursively process children and concatenate
    parts = []
    for child in node.children:
        parts.append(_node_to_markdown(child, list_level=list_level))
    return _clean_whitespace(" ".join(p for p in parts if p))

# =============================================================================
#                           LIST CONVERSION
# =============================================================================

def _list_to_markdown(list_tag: Tag, indent: int = 0) -> str:
    """
    Convert <ul> or <ol> to markdown. indent denotes nesting level (0 = top).
    """
    lines = []
    is_ordered = (list_tag.name.lower() == 'ol')
    idx = 1
    for li in [c for c in list_tag.children if isinstance(c, Tag) and c.name.lower() == 'li']:
        # li may contain <p> or direct text or nested lists
        # Collect li text excluding nested lists
        parts = []
        for child in li.children:
            if isinstance(child, Tag) and child.name.lower() in ('ul', 'ol'):
                # nested list, handle after current line
                continue
            parts.append(_node_to_markdown(child, list_level=indent+1))
        line_text = _clean_whitespace(" ".join(p for p in parts if p))
        prefix = f"{idx}." if is_ordered else "-"
        indent_spaces = "  " * indent
        if line_text:
            lines.append(f"{indent_spaces}{prefix} {line_text}")
        else:
            lines.append(f"{indent_spaces}{prefix}")
        # handle nested lists inside this li
        for child in li.children:
            if isinstance(child, Tag) and child.name.lower() in ('ul', 'ol'):
                nested = _list_to_markdown(child, indent=indent+1)
                if nested:
                    lines.append(nested)
        idx += 1
    return "\n".join(lines) + "\n\n" if lines else ""

# =============================================================================
#                           TABLE CONVERSION
# =============================================================================

def _table_to_markdown(table_tag: Tag) -> str:
    """
    Convert an HTML <table> to Markdown.
    - Detects header rows properly using <th>.
    - Preserves <caption> as a heading above the table.
    - Handles key/value and regular tables.
    - Properly handles colspan/rowspan by expanding cells.
    """
    # Table caption
    caption = table_tag.find('caption')
    caption_text = _clean_whitespace(caption.get_text()) if caption else ''
    md_parts = []
    if caption_text:
        md_parts.append(f"**{caption_text}**\n")

    def process_cell_content(cell: Tag) -> str:
        """Process cell content with proper escaping and whitespace handling"""
        # Check if cell contains macros first (macros have priority over dates)
        has_macro = cell.find('ac:structured-macro') or cell.find('ac:macro')
        
        if has_macro:
            # Process macros normally - they may contain dates in parameters
            cell_text = _node_to_markdown(cell)
        else:
            # Try to extract date if no macros present
            date_str = _extract_and_format_date(cell)
            if date_str:
                # If date found, use it (already cleaned)
                return _escape_pipe(date_str)
            
            # Otherwise process normally
            cell_text = _node_to_markdown(cell)
        
        # Preserve structure but normalize excessive whitespace
        cell_text = _clean_whitespace(cell_text, keep_newlines=False)
        # Escape pipes in cell content
        cell_text = _escape_pipe(cell_text)
        return cell_text

    # Collect all rows with proper expansion
    rows_all = table_tag.find_all("tr")
    if not rows_all:
        return ""

    # Detect 2-column key/value table (each row has exactly 2 cells total)
    is_key_value_table = len(rows_all) > 1 and all(
        len(tr.find_all(["th", "td"])) == 2 
        for tr in rows_all
    )
    
    if is_key_value_table:
        # Process as key-value pairs
        kv_rows = []
        for tr in rows_all:
            cells = tr.find_all(["th", "td"])
            if len(cells) == 2:
                key = process_cell_content(cells[0])
                value = process_cell_content(cells[1])
                kv_rows.append(f"| {key} | {value} |")
        
        if kv_rows:
            # Add header separator for Markdown validity
            header_sep = "| --- | --- |"
            return "\n".join([kv_rows[0], header_sep] + kv_rows[1:]) + "\n\n"

    # Process regular table
    rows = []
    headers = []
    max_cols = 0
    
    for tr in rows_all:
        cells = []
        for cell in tr.find_all(["th", "td"]):
            cell_text = process_cell_content(cell)
            
            # Handle colspan by repeating cell
            colspan = int(cell.get('colspan', 1))
            cells.append(cell_text)
            for _ in range(colspan - 1):
                cells.append("")  # Add empty cells for colspan
        
        if not cells:
            continue
            
        max_cols = max(max_cols, len(cells))
        
        # Check if this row contains headers
        has_th = bool(tr.find_all("th"))
        if has_th and not headers:
            headers = cells
        else:
            rows.append(cells)

    # Return empty if no content
    if not rows and not headers:
        return ""

    # Normalize all rows to same column count
    if headers:
        # Pad header to max_cols
        while len(headers) < max_cols:
            headers.append("")
        
        sep = ["---"] * len(headers)
        md_lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(sep) + " |"
        ]
        
        for r in rows:
            while len(r) < len(headers):
                r.append("")
            md_lines.append("| " + " | ".join(r[:len(headers)]) + " |")
        
        md_parts.append("\n".join(md_lines))
    else:
        # No headers - add separator as first row
        sep = ["---"] * max_cols
        md_lines = ["| " + " | ".join(sep) + " |"]
        
        for r in rows:
            while len(r) < max_cols:
                r.append("")
            md_lines.append("| " + " | ".join(r[:max_cols]) + " |")
        
        md_parts.append("\n".join(md_lines))

    return "\n".join(md_parts) + "\n\n"

# =============================================================================
#                           MACRO RENDERERS
# =============================================================================

def _render_macro(name: str, params: Dict[str, str], body_html: str, metadata: Dict[str, str] = None) -> str:
    """Render common macros; fall back to placeholder for unknown macros."""
    n = (name or "").lower().strip()
    
    # Skip UI macros - they're not useful for page analysis
    if n in _UI_MACROS:
        return ""

    if n in ('code', 'code-block'):
        # attempt to extract plain text body or code element
        try:
            soup = BeautifulSoup(body_html, "html.parser")
            code_body = soup.find('ac:plain-text-body') or soup.find('pre') or soup
            language = params.get('language') or params.get('lang') or ''
            code_text = code_body.get_text() if code_body else soup.get_text()
            return f"\n```{language}\n{code_text.rstrip()}\n```\n"
        except Exception:
            return "\n```\n" + _clean_whitespace(BeautifulSoup(body_html or "", "html.parser").get_text()) + "\n```\n"

    if n == 'toc' or n == 'table-of-contents':
        # don't attempt perfect reproduction — provide placeholder or skip
        return "\n<!-- TOC omitted: Table of Contents macro -->\n\n"

    if n in ('expand', 'details'):
        soup = BeautifulSoup(body_html or "", "html.parser")
        # Only use explicit title or label parameters
        title_param = params.get('title') or params.get('label')
        title = _clean_whitespace(title_param) if title_param else ""
        
        # Convert inner content to markdown - process children individually
        parts = []
        for child in (soup.body.contents if soup.body else soup.contents):
            parts.append(_node_to_markdown(child))
        inner = "\n".join(p for p in parts if p and p.strip())
        
        # Ensure proper spacing around tables in details
        inner = inner.strip()
        
        # Do NOT fall back to body text; Confluence "status" macros may leak text like "DRAFT"
        if title:
            return f"\n<details>\n<summary>{title}</summary>\n\n{inner}\n\n</details>\n\n"
        else:
            return f"\n<details>\n\n{inner}\n\n</details>\n\n"



    if n == 'status':
        # status macro holds title/colour
        title = params.get('title') or BeautifulSoup(body_html or "", "html.parser").get_text(strip=True)
        colour = params.get('colour') or params.get('color') or ''
        return f"[STATUS: {title}]" if title else "[STATUS]"

    if n in ('viewpdf', 'view-file', 'viewfile'):
        # display a placeholder link to file, param often includes name or file
        name = params.get('name') or params.get('file') or ''
        if name:
            return f"[PDF: {name}]"
        # try to parse body for attachment
        soup = BeautifulSoup(body_html or "", "html.parser")
        att = soup.find('ri:attachment')
        if att:
            fname = att.get('ri:filename') or att.get('filename') or ''
            return f"[Attachment: {fname}]" if fname else "[Attachment]"
        return "[PDF]"

    if n in ('include', 'include-page', 'excerpt-include', 'excerpt'):
        # Format as clear reference to another page
        page = params.get('page') or params.get('name') or params.get('pageTitle') or ''
        space = params.get('space') or params.get('spaceKey') or ''
        
        # Clean, readable format that clearly indicates it's a reference
        if page and space:
            return f"[INCLUDE-REF: {page} (Space: {space})]"
        elif page:
            return f"[INCLUDE-REF: {page}]"
        elif space:
            return f"[INCLUDE-REF: Space {space}]"
        else:
            return "[INCLUDE-REF]"

    if n in ('jira', 'jira-issues', 'jira-issue'):
        # Format as clear Jira reference with meaningful context
        server = params.get('server') or params.get('servername') or 'System Jira'
        jql = params.get('jqlQuery') or params.get('jql') or params.get('query') or ''
        count = params.get('count', '').lower() == 'true'
        
        # Extract project name from JQL if available (more meaningful than full query)
        project_name = ''
        if jql:
            # Try to extract project name from patterns like: project = "Project Name"
            import re
            project_match = re.search(r'project\s*=\s*["\']([^"\']+)["\']', jql, re.I)
            if project_match:
                project_name = project_match.group(1)
        
        # Format differently based on whether it's displaying count or full issues
        # When count=true, it displays as "N issues" in Confluence
        # When count=false/missing, it displays the full issue list
        if count:
            # This would display as "29 issues", "18 issues" etc. in rendered Confluence
            indicator = "N issues"  # Placeholder for the dynamic count
            if project_name:
                return f"{indicator} [JIRA: {project_name}]"
            else:
                return f"{indicator} [JIRA: {server}]"
        else:
            # Full issue list reference
            if project_name:
                return f"[JIRA-REF: {server} - {project_name}]"
            else:
                return f"[JIRA-REF: {server}]"

    if n in ('task-list', 'tasklist'):
        soup = BeautifulSoup(body_html or "", "html.parser")
        tasks_md = []
        for task in soup.find_all('ac:task'):
            status = task.find('ac:task-status')
            body = task.find('ac:task-body')
            checked = (status and status.get_text(strip=True).lower() == 'complete')
            text = _clean_whitespace(body.get_text(" ", strip=True) if body else '')
            if not text:
                text = "(no description)"
            checkbox = "[x]" if checked else "[ ]"
            tasks_md.append(f"- {checkbox} {text}")
        return "\n".join(tasks_md) + "\n"

    if n == 'panel':
        colour = params.get('bgColor') or params.get('color') or ''
        soup = BeautifulSoup(body_html or "", "html.parser")
        # Process children individually to preserve block structure
        parts = []
        for child in (soup.body.contents if soup.body else soup.contents):
            parts.append(_node_to_markdown(child))
        inner_md = "\n".join(p for p in parts if p and p.strip())
        # Escape line breaks separately to avoid backslashes in f-string expressions
        escaped_md = inner_md.replace("\n", "\n> ")
        return f"\n> **Panel ({colour}):**\n>\n> {escaped_md}\n"

    if n in ('index', 'content-by-label', 'children'):
        # These macros display navigation/reference lists to other pages
        # They should be treated as links/references, not as empty content
        if n == 'children':
            # Children macro displays a list of child pages with links
            return "[PAGE-REF: Child pages list]"
        elif n == 'content-by-label':
            # Content by label shows pages with specific labels
            labels = params.get('labels') or params.get('cql') or ''
            if labels:
                return f"[PAGE-REF: Pages with labels - {labels}]"
            return "[PAGE-REF: Pages by label]"
        else:  # index
            # Index macro creates a table of contents with page links
            return "[PAGE-REF: Page index]"

    if n in ('roadmap', 'roadmap-planner'):
        clean_params = {k: v for k, v in params.items() if len(v) < 80 and not v.startswith('%7B')}
        title = params.get('title') or params.get('label') or 'Roadmap'
        param_str = ", ".join(f"{k}={v}" for k, v in clean_params.items())
        return f"[MACRO: {title} ({param_str})]"


    # generic ac:link with ri:user handled earlier; other macros might need fallback:
    # Render macro with its parameters and a short body preview
    preview = _clean_whitespace(BeautifulSoup(body_html or "", "html.parser").get_text(" ", strip=True))
    param_str = ", ".join(f"{k}={v}" for k, v in params.items()) if params else ""
    meta_str = ""
    if metadata:
        meta_str = "  <!-- " + ", ".join(f"{k}={v}" for k, v in metadata.items()) + " -->"

    if preview:
        return f"[MACRO: {n} {param_str} -> {preview}]{meta_str}"
    
    return f"[MACRO: {n} {param_str}]{meta_str}"

# =============================================================================
#                           PUBLIC API
# =============================================================================

def convert_html_to_markdown(html_str: str) -> str:
    """
    Convert Confluence XHTML (storage format) fragment to Markdown.
    """
    if not html_str:
        return ""

    # parse
    try:
        soup = BeautifulSoup(html_str, "html.parser")
    except FeatureNotFound:
        soup = BeautifulSoup(html_str, "lxml")

    # Remove scripts/styles
    for elt in soup(['script', 'style']):
        elt.decompose()


    # Convert top-level children and join
    parts = []
    for child in soup.body.contents if soup.body else soup.contents:
        parts.append(_node_to_markdown(child))
    md = "\n".join(p for p in parts if p and p.strip())

    # Post-process: collapse many blank lines into max two
    md = re.sub(r'\n\s*\n\s*\n+', '\n\n', md)
    # md = re.sub(r'[ \t]+(\n)', r'\1', md)
    md = re.sub(r'[ \t]+(\n)(?!\|)', r'\1', md)

    return md.strip() + "\n"

# =============================================================================
#                           MAIN EXECUTION (FOR TESTING)
# =============================================================================

if __name__ == "__main__":
    dump_file = DEFAULT_CONFLUENCE_DATA_PATH

    with open(dump_file, "r", encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]

    record = items[DEFAULT_TEST_INDEX]
    html_body = record.get("body", "")
    md = convert_html_to_markdown(html_body)
    
    print("=" * 80)
    print(f"HTML BODY (Record #{DEFAULT_TEST_INDEX})")
    print("=" * 80)
    print(html_body)
    print("\n" + "=" * 80)
    print(f"CONVERTED MARKDOWN (Record #{DEFAULT_TEST_INDEX})")
    print("=" * 80)
    print(md)
