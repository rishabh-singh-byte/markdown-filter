"""
Label Studio Async Processor
=============================
Process Label Studio data to determine if pages are gibberish or useful.
Uses async processing with progress tracking via tqdm.
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

from page_decider import is_page_gibberish
from collect import collect_document_data

# =============================================================================
#                           CONFIGURATION PARAMETERS
# =============================================================================

DEFAULT_INPUT_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/label_studio/fetch_tasks/label_studio_combined_processed.jsonl"
DEFAULT_OUTPUT_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/results/label_studio_gibberish_results_3.jsonl"
DEFAULT_BATCH_SIZE = 10

# =============================================================================
#                           ASYNC PROCESSING FUNCTIONS
# =============================================================================

async def process_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single document to determine if it's gibberish.
    
    Args:
        doc: Document dictionary with all fields from input file
    
    Returns:
        Original document dict with added 'result' field containing decision info
    """
    try:
        # Collect document data for analysis
        doc_data = collect_document_data(doc)
        
        # Determine if page is gibberish
        page_is_gibberish = is_page_gibberish(doc_data)[0]
        
        # Create result dictionary
        result = {
            "is_gibberish": "yes" if page_is_gibberish else "no",
        }
        
        # Add result to original document
        output_doc = doc.copy()
        output_doc["result"] = result
        
        return output_doc
        
    except Exception as e:
        # Handle errors gracefully
        output_doc = doc.copy()
        output_doc["result"] = {
            "is_gibberish": None,
            "status": "ERROR",
            "reason": f"Processing error: {str(e)}",
            "error": str(e)
        }
        return output_doc


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
        List of processed documents with results
    """
    results = []
    
    # Create a semaphore to limit concurrent processing
    semaphore = asyncio.Semaphore(batch_size)
    
    async def process_with_semaphore(doc):
        async with semaphore:
            return await process_document(doc)
    
    # Process all documents with progress bar
    tasks = [process_with_semaphore(doc) for doc in documents]
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


def write_jsonl(documents: List[Dict[str, Any]], file_path: str):
    """
    Write documents to JSONL file.
    
    Args:
        documents: List of document dictionaries
        file_path: Path to output JSONL file
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        for doc in tqdm(documents, desc="Writing output file"):
            f.write(json.dumps(doc, ensure_ascii=False) + '\n')

# =============================================================================
#                           MAIN ASYNC EXECUTION
# =============================================================================

async def main_async(input_file: str, output_file: str, batch_size: int = 10):
    """
    Main async function to process all documents.
    
    Args:
        input_file: Path to input JSONL file
        output_file: Path to output JSONL file
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
        if doc.get("result", {}).get("is_gibberish") == "yes"
    )
    useful_count = sum(
        1 for doc in processed_documents 
        if doc.get("result", {}).get("is_gibberish") == "no"
    )
    error_count = sum(
        1 for doc in processed_documents 
        if doc.get("result", {}).get("status") == "ERROR"
    )
    
    print(f"Results:")
    print(f"  ✅ Useful pages: {useful_count}")
    print(f"  ❌ Gibberish pages: {gibberish_count}")
    print(f"  ⚠️  Errors: {error_count}\n")
    
    # Write output
    print("Step 3: Writing output file...")
    write_jsonl(processed_documents, output_file)
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
