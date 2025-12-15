"""PDF helper - extract text and tables from PDF files."""

import pdfplumber

from logs.logger import get_logger

logger = get_logger("pdf")


def extract_pdf_text(path: str) -> str:
    """Extract all text from a PDF file.

    Args:
        path: Path to the PDF file.

    Returns:
        str: Extracted text from all pages.
    """
    try:
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"=== Page {i + 1} ===\n{page_text}")
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return f"PDF extraction error: {e}"


def extract_pdf_tables(path: str) -> list:
    """Extract tables from a PDF file.

    Args:
        path: Path to the PDF file.

    Returns:
        list: List of tables, each table is a list of rows.
    """
    try:
        all_tables = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                all_tables.extend(tables)
        return all_tables
    except Exception as e:
        logger.error(f"PDF table extraction failed: {e}")
        return []
