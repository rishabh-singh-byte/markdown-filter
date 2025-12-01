"""
Confluence Document Analyzer
=============================
Analyze Confluence markdown documents to determine if pages are gibberish or useful.
Uses async processing with progress tracking via tqdm.

Output Format:
    - url: Document URL
    - decision: "gibberish" or "useful" 
    - index: Sequential document index
    - page_title: Document title
"""

# =============================================================================
#                           IMPORTS
# =============================================================================

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from tqdm.asyncio import tqdm_asyncio
from tqdm import tqdm

from filter.main.page_decider import is_page_gibberish
from filter.main.collect import collect_document_data

# =============================================================================
#                           CONFIGURATION PARAMETERS
# =============================================================================

DEFAULT_INPUT_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/data/confluence_markdown.jsonl"
DEFAULT_OUTPUT_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/results/confluence_analysis_results_b.json"
DEFAULT_BATCH_SIZE = 10

# =============================================================================
#                           ASYNC PROCESSING FUNCTIONS
# =============================================================================

async def process_document(doc: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Process a single document to determine if it's gibberish.
    
    Args:
        doc: Document dictionary with all fields from input file
        index: Sequential index of the document (0-based)
    
    Returns:
        Simplified dict with only: url, decision, index, page_title
    """
    try:
        # Collect document data for analysis
        doc_data = collect_document_data(doc)
        
        # Determine if page is gibberish
        page_is_gibberish = is_page_gibberish(doc_data)[0]
        
        # Create simplified output with only required fields
        return {
            "url": doc.get("url", ""),
            "decision": "gibberish" if page_is_gibberish else "useful",
            "index": index,
            "page_title": doc.get("title", "")
        }
        
    except Exception as e:
        # Handle errors gracefully - still return required fields
        return {
            "url": doc.get("url", ""),
            "decision": f"error: {str(e)}",
            "index": index,
            "page_title": doc.get("title", "")
        }


async def process_documents_batch(
    documents: List[Dict[str, Any]], 
    batch_size: int = 10
) -> List[Dict[str, Any]]:
    """
    Process documents in batches with async concurrency.
    
    Args:
        documents: List of document dictionaries
        batch_size: Number of documents to process concurrently
    
    Returns:
        List of processed documents with results (url, decision, index, page_title)
    """
    results = []
    
    # Create a semaphore to limit concurrent processing
    semaphore = asyncio.Semaphore(batch_size)
    
    async def process_with_semaphore(doc_with_index):
        doc, index = doc_with_index
        async with semaphore:
            return await process_document(doc, index)
    
    # Process all documents with progress bar, passing index
    tasks = [process_with_semaphore((doc, idx)) for idx, doc in enumerate(documents)]
    results = await tqdm_asyncio.gather(
        *tasks, 
        desc="Processing documents",
        total=len(documents)
    )
    
    return results

# =============================================================================
#                           FILE I/O FUNCTIONS
# =============================================================================

def read_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """
    Read documents from JSONL file.
    
    Args:
        file_path: Path to JSONL file
    
    Returns:
        List of document dictionaries
    """
    documents = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc="Reading input file"):
            if line.strip():
                documents.append(json.loads(line))
    return documents


def write_json(documents: List[Dict[str, Any]], file_path: str):
    """
    Write documents to JSON file as a single array.
    
    Args:
        documents: List of document dictionaries
        file_path: Path to output JSON file
    """
    print("Writing output file...")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

# =============================================================================
#                           MAIN ASYNC EXECUTION
# =============================================================================

async def main_async(input_file: str, output_file: str, batch_size: int = 10):
    """
    Main async function to process all documents.
    
    Args:
        input_file: Path to input JSONL file
        output_file: Path to output JSON file
        batch_size: Number of documents to process concurrently
    """
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Batch size: {batch_size}\n")
    
    # Read input documents
    print("Step 1: Reading input file...")
    documents = read_jsonl(input_file)
    print(f"Loaded {len(documents)} documents\n")
    
    # Process documents
    print("Step 2: Processing documents...")
    processed_documents = await process_documents_batch(documents, batch_size)
    print(f"Processed {len(processed_documents)} documents\n")
    
    # Count results
    gibberish_count = sum(
        1 for doc in processed_documents 
        if doc.get("decision") == "gibberish"
    )
    useful_count = sum(
        1 for doc in processed_documents 
        if doc.get("decision") == "useful"
    )
    error_count = sum(
        1 for doc in processed_documents 
        if doc.get("decision", "").startswith("error:")
    )
    
    print(f"Results:")
    print(f"  ✅ Useful pages: {useful_count}")
    print(f"  ❌ Gibberish pages: {gibberish_count}")
    print(f"  ⚠️  Errors: {error_count}\n")
    
    # Write output
    print("Step 3: Writing output file...")
    write_json(processed_documents, output_file)
    print(f"✅ Done! Results saved to: {output_file}")

# =============================================================================
#                           MAIN ENTRY POINT
# =============================================================================

def main():
    """
    Main entry point for the script.
    """
    input_file = DEFAULT_INPUT_FILE
    output_file = DEFAULT_OUTPUT_FILE
    batch_size = DEFAULT_BATCH_SIZE
    
    # Run async processing
    asyncio.run(main_async(input_file, output_file, batch_size))


if __name__ == "__main__":
    main()
