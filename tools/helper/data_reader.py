"""Read and convert downloaded data files to text."""
import sys
import json
import asyncio
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import error, info, success


async def read_csv(filepath: str) -> dict:
    """Read CSV and convert to readable text."""
    path = Path(filepath)
    
    if not path.exists():
        error("reader", f"file not found: {path}")
        return {"success": False, "text": "", "df": None, "error": "file not found"}
    
    info("reader", f"reading csv: {path.name}")
    
    try:
        loop = asyncio.get_event_loop()
        
        def _read():
            df = pd.read_csv(path)
            text_parts = [
                f"CSV: {path.name}",
                f"Rows: {len(df)}, Columns: {len(df.columns)}",
                f"Columns: {', '.join(df.columns)}",
                "",
                "First 5 rows:",
                df.head().to_string(),
                "",
                "Last 3 rows:",
                df.tail(3).to_string(),
            ]
            return df, "\n".join(text_parts)
        
        df, text = await loop.run_in_executor(None, _read)
        
        success("reader", f"read {len(df)} rows")
        return {"success": True, "text": text, "df": df, "error": ""}
    except Exception as e:
        error("reader", str(e))
        return {"success": False, "text": "", "df": None, "error": str(e)}


async def read_json(filepath: str) -> dict:
    """Read JSON file."""
    path = Path(filepath)
    
    if not path.exists():
        error("reader", f"file not found: {path}")
        return {"success": False, "data": None, "text": "", "error": "file not found"}
    
    info("reader", f"reading json: {path.name}")
    
    try:
        data = json.loads(path.read_text())
        text = json.dumps(data, indent=2)
        
        success("reader", f"read json with {len(text)} chars")
        return {"success": True, "data": data, "text": text, "error": ""}
    except Exception as e:
        error("reader", str(e))
        return {"success": False, "data": None, "text": "", "error": str(e)}


async def read_excel(filepath: str) -> dict:
    """Read Excel file."""
    path = Path(filepath)
    
    if not path.exists():
        error("reader", f"file not found: {path}")
        return {"success": False, "text": "", "df": None, "error": "file not found"}
    
    info("reader", f"reading excel: {path.name}")
    
    try:
        loop = asyncio.get_event_loop()
        
        def _read():
            df = pd.read_excel(path)
            text_parts = [
                f"Excel: {path.name}",
                f"Rows: {len(df)}, Columns: {len(df.columns)}",
                f"Columns: {', '.join(str(c) for c in df.columns)}",
                "",
                "First 5 rows:",
                df.head().to_string(),
            ]
            return df, "\n".join(text_parts)
        
        df, text = await loop.run_in_executor(None, _read)
        
        success("reader", f"read {len(df)} rows from excel")
        return {"success": True, "text": text, "df": df, "error": ""}
    except Exception as e:
        error("reader", str(e))
        return {"success": False, "text": "", "df": None, "error": str(e)}


async def read_file(filepath: str) -> dict:
    """
    Read any file type and return its content.
    Automatically detects file type.
    """
    path = Path(filepath)
    
    if not path.exists():
        return {"success": False, "text": "", "error": "file not found"}
    
    ext = path.suffix.lower()
    
    if ext == ".csv":
        return await read_csv(filepath)
    elif ext == ".json":
        return await read_json(filepath)
    elif ext in (".xlsx", ".xls"):
        return await read_excel(filepath)
    elif ext == ".pdf":
        from tools.helper.pdf_reader import read_pdf
        return await read_pdf(filepath)
    elif ext in (".txt", ".md", ".html", ".xml"):
        info("reader", f"reading text file: {path.name}")
        text = path.read_text()
        success("reader", f"read {len(text)} chars")
        return {"success": True, "text": text, "error": ""}
    else:
        # Try as binary
        info("reader", f"reading binary file: {path.name}")
        try:
            data = path.read_bytes()
            return {"success": True, "bytes": data, "size": len(data), "error": ""}
        except Exception as e:
            return {"success": False, "error": str(e)}
