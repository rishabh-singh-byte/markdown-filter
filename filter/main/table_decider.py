"""
Table Gibberish Decider
========================
Determines if a table contains gibberish or useful content based on meaningful content analysis.
"""
import json
from collect import collect_document_data

# =============================================================================
#                           CONFIGURATION PARAMETERS
# =============================================================================

DEFAULT_DATA_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/data/confluence_markdown.jsonl"
DEFAULT_TEST_INDEX = 6687
MEANINGFUL_WORDS_THRESHOLD = 3

# =============================================================================
#                           CORE FUNCTIONS
# =============================================================================

def is_table_gibberish(table_analysis):
    """
    Determine if a table is gibberish based on meaningful content (excluding headings and placeholders).
    
    Decision Criteria (ANY of these makes the table USEFUL):
    1. Meaningful words ≥ 2 (excludes headings, placeholders like draft/tbd/yes/no)
    2. Contains links (URLs, hyperlinks)
    3. Contains images (image references)
    4. Contains file references (PDFs, docs, etc.)
    5. Contains user mentions ([~username])
    6. Pre-computed is_useful_table flag is True
    
    Returns:
        bool: True if gibberish, False if useful
        dict: Decision breakdown with reasons
    """
    if not table_analysis:
        return True, {"reason": "Empty or invalid table analysis"}
    
    # Extract metrics (all exclude headings and placeholders)
    meaningful_words = table_analysis.get('meaningful_words', 0)
    total_words = table_analysis.get('words', 0)
    placeholder_words = table_analysis.get('placeholder_words', 0)
    links = table_analysis.get('links', 0)
    images = table_analysis.get('images', 0)
    files = table_analysis.get('files', 0)
    mentions = table_analysis.get('mentions', 0)
    is_useful = table_analysis.get('is_useful_table', False)
    
    # Track reasons for decision
    useful_indicators = []
    
    # Check meaningful words (excludes headings and placeholders)
    if meaningful_words >= MEANINGFUL_WORDS_THRESHOLD:
        useful_indicators.append(f"{meaningful_words} meaningful words (excl. headings & placeholders)")
    
    # Check links
    if links > 0:
        useful_indicators.append(f"{links} link(s)")
    
    # Check images
    if images > 0:
        useful_indicators.append(f"{images} image(s)")
    
    # Check file references
    if files > 0:
        useful_indicators.append(f"{files} file reference(s)")
    
    # Check user mentions
    if mentions > 0:
        useful_indicators.append(f"{mentions} user mention(s)")
    
    # Check pre-computed flag
    if is_useful:
        useful_indicators.append("pre-computed useful flag")
    
    # Decision logic
    is_gibberish = len(useful_indicators) == 0
    
    decision_info = {
        "is_gibberish": is_gibberish,
        "meaningful_words": meaningful_words,
        "total_words": total_words,
        "placeholder_words": placeholder_words,
        "links": links,
        "images": images,
        "files": files,
        "mentions": mentions,
        "useful_indicators": useful_indicators,
        "reason": "No useful content found" if is_gibberish else f"Useful: {', '.join(useful_indicators)}"
    }
    
    return is_gibberish, decision_info

# =============================================================================
#                           MAIN EXECUTION
# =============================================================================

def main():
    index = DEFAULT_TEST_INDEX
    dump_file_name = DEFAULT_DATA_FILE

    with open(dump_file_name, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f):
            if line_number != index:
                continue  # skip lines until the desired index

            data = json.loads(line)
            doc_id = data.get("id")
            doc_data = collect_document_data(data)
            print(f"URL: {doc_data['url']}")
            print(f"Title: {doc_data['title']}")

            tables = doc_data.get('tables', [])
            if not tables:
                print(f"Document {doc_id} has no tables.")
                continue

            print(f"\nDocument {doc_id} contains {len(tables)} table(s):")
            print(f"Useful Tables: {doc_data.get('useful_table_count', 0)}")
            print(f"Gibberish Tables: {doc_data.get('gibberish_table_count', 0)}\n")
            
            for table in tables:
                table_index = table.get('table_index')
                is_gibberish, decision_info = is_table_gibberish(table.get('analysis', {}))
                status = "❌ Gibberish" if is_gibberish else "✅ Useful"
                
                print(f"Table {table_index} is {status}")
                print(f"  Decision: {decision_info['reason']}")
                print(f"  Metrics:")
                print(f"    • Meaningful Words: {decision_info['meaningful_words']} (excl. headings & placeholders)")
                print(f"    • Total Words: {decision_info['total_words']} (excl. headings)")
                print(f"    • Placeholder Words: {decision_info['placeholder_words']}")
                print(f"    • Links: {decision_info['links']}")
                print(f"    • Images: {decision_info['images']}")
                print(f"    • Files: {decision_info['files']}")
                print(f"    • Mentions: {decision_info['mentions']}")
                
                print("\n  Table Content:")
                for row in table.get('raw_table', []):
                    print(f"    {row}")
                print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
