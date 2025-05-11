from typing import List, Dict, Any
import os
import time
from tqdm import tqdm

from backend.app_modules.config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks of specified size."""
    if not text:
        return []
    
    # If text is shorter than chunk_size, return it as a single chunk
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Define chunk end position
        end = start + chunk_size
        
        # Adjust to not cut words in the middle
        if end < len(text):
            # Try to find a natural break point
            break_chars = ["\n\n", "\n", ". ", "! ", "? ", "；", "。", "，", "、", " "]
            
            for char in break_chars:
                # Search for the break character in a window near the end of the chunk
                search_window = text[end - min(100, chunk_overlap):end + 100]
                break_pos = search_window.find(char)
                
                if break_pos != -1:
                    # Adjust end position to include the break character
                    end = end - min(100, chunk_overlap) + break_pos + len(char)
                    break
        
        # Get the chunk
        chunk = text[start:min(end, len(text))]
        chunks.append(chunk)
        
        # Move start position considering overlap
        if end >= len(text):
            break
            
        start = end - chunk_overlap
    
    return chunks


def safe_mkdir(path: str) -> None:
    """Safely create a directory and all parent directories."""
    os.makedirs(path, exist_ok=True)


def rate_limit(min_time_between_calls: float = 0.5) -> None:
    """Simple rate limiting function to prevent API throttling."""
    time.sleep(min_time_between_calls)


def process_with_progress(items: List[Any], process_fn, description: str = "Processing") -> List[Any]:
    """Process a list of items with a progress bar."""
    results = []
    for item in tqdm(items, desc=description):
        result = process_fn(item)
        results.append(result)
    return results 