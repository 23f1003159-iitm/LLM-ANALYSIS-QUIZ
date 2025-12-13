"""Read and extract text from PDF files."""
import sys
import asyncio
from pathlib import Path
import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import error, info, success


async def read_pdf(filepath: str) -> dict:
    """
    Extract all text from a PDF file.
    
    Args:
        filepath: Path to PDF file
    
    Returns:
        dict with success, text, pages
    """
    path = Path(filepath)
    
    if not path.exists():
        error("pdf", f"file not found: {path}")
        return {"success": False, "text": "", "pages": 0, "error": "file not found"}
    
    info("pdf", f"reading {path.name}")
    
    try:
        loop = asyncio.get_event_loop()
        
        def _read():
            doc = fitz.open(path)
            text_parts = []
            
            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"--- PAGE {page_num} ---\n{page_text}")
            
            doc.close()
            return text_parts
        
        text_parts = await loop.run_in_executor(None, _read)
        full_text = "\n\n".join(text_parts)
        
        success("pdf", f"extracted {len(text_parts)} pages, {len(full_text)} chars")
        
        return {
            "success": True,
            "text": full_text,
            "pages": len(text_parts),
            "error": ""
        }
    except Exception as e:
        error("pdf", str(e))
        return {"success": False, "text": "", "pages": 0, "error": str(e)}


async def read_pdf_tables(filepath: str) -> dict:
    """
    Extract tables from PDF as text.
    
    Args:
        filepath: Path to PDF file
    
    Returns:
        dict with success, tables list
    """
    path = Path(filepath)
    
    if not path.exists():
        return {"success": False, "tables": [], "error": "file not found"}
    
    info("pdf", f"extracting tables from {path.name}")
    
    try:
        loop = asyncio.get_event_loop()
        
        def _extract_tables():
            doc = fitz.open(path)
            tables = []
            
            for page_num, page in enumerate(doc, 1):
                # Get text blocks which often contain tabular data
                blocks = page.get_text("blocks")
                for block in blocks:
                    text = block[4] if len(block) > 4 else ""
                    # Look for table-like patterns (multiple columns)
                    if text.count("\t") > 2 or text.count("  ") > 5:
                        tables.append({
                            "page": page_num,
                            "text": text
                        })
            
            doc.close()
            return tables
        
        tables = await loop.run_in_executor(None, _extract_tables)
        
        success("pdf", f"found {len(tables)} table-like blocks")
        return {"success": True, "tables": tables, "error": ""}
    except Exception as e:
        error("pdf", str(e))
        return {"success": False, "tables": [], "error": str(e)}
