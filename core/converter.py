"""Core Converter - Convert scraped data to LLM-ready context."""

from helpers import download, read_text, transcribe_url
from helpers.bs64_encoding import decode_base64
from helpers.pdf import extract_pdf_text
from helpers.sql import download_and_query
from helpers.unzip_zip import unzip
from logs.logger import get_logger

logger = get_logger("converter")


async def convert(scraped: dict) -> dict:
    """Convert scraped data into LLM-ready format.

    Processes all scraped data (audio, files, links) and formats it into
    a context string that the LLM can understand, along with structured data.

    Handles:
    - Audio transcription
    - CSV file reading
    - SQL database querying
    - ZIP file extraction
    - Base64 decoding
    - JSON parsing

    Args:
        scraped: Scraped data dictionary from scraper containing:
            - url (str): Original URL
            - text (str): Page text
            - audio (list): Audio URLs
            - files (list): File dicts with href and text
            - links (list): Link dicts
            - params (dict): Extracted parameters

    Returns:
        dict: Converted data containing:
            - context (str): LLM-ready formatted text
            - data (dict): Structured data (df, params, transcripts, etc.)

    Example:
        >>> scraped = {'url': '...', 'text': '...', 'files': [...]}
        >>> result = await convert(scraped)
        >>> print(result['context'][:100])
        URL: https://quiz.com/q1
        PAGE TEXT:
        Calculate sum...
    """
    parts = []
    data = {}

    # Page info
    parts.append(f"URL: {scraped['url']}")
    parts.append(f"PAGE TEXT:\n{scraped['text']}")

    # Parameters
    if scraped.get("params"):
        parts.append(f"EXTRACTED PARAMS: {scraped['params']}")
        data["params"] = scraped["params"]

    # Transcribe audio
    for audio_url in scraped.get("audio", []):
        try:
            logger.debug(f"Transcribing audio: {audio_url}")
            transcript = await transcribe_url(audio_url)
            parts.append(f"AUDIO TRANSCRIPT:\n{transcript}")
            data["audio_transcript"] = transcript
        except Exception as e:
            logger.error(f"Audio transcription error: {e}")
            parts.append(f"AUDIO ERROR: {e}")

    # Download and read files
    for file_info in scraped.get("files", []):
        href = file_info["href"]
        try:
            logger.debug(f"Processing file: {href}")
            path = await download(href)

            # Handle PDF files first (binary, can't read_text)
            if href.endswith(".pdf"):
                try:
                    pdf_text = extract_pdf_text(path)
                    parts.append(f"PDF CONTENT:\n{pdf_text}")
                    data["pdf_content"] = pdf_text
                    data["pdf_path"] = path
                except Exception as pdf_e:
                    parts.append(f"PDF ERROR ({href}): {pdf_e}")
                continue

            # Handle SQLite/DB files (binary, can't read_text)
            if href.endswith(".sqlite") or href.endswith(".db"):
                try:
                    results = await download_and_query(
                        href, "SELECT COUNT(*) FROM users WHERE age > 18"
                    )
                    parts.append(f"SQL QUERY RESULT (users age>18): {results[0][0]}")
                    data["sql_result"] = results[0][0]
                except Exception as sql_e:
                    parts.append(f"SQL FILE ({href}): Error - {sql_e}")
                continue

            # Read text for text-based formats
            content = read_text(path)

            if href.endswith(".csv"):
                parts.append(f"CSV DATA:\n{content}")
                data["csv_content"] = content
                data["csv_path"] = path

            elif href.endswith(".sql"):
                parts.append(f"SQL FILE ({href}): Downloaded, content:\n{content[:1000]}")
                data["sql_content"] = content

            elif href.endswith(".json"):
                parts.append(f"JSON DATA:\n{content}")
                data["json_content"] = content

            elif href.endswith(".zip"):
                # ZIP file - extract and read contents
                try:
                    extracted_files = unzip(path)
                    zip_contents = []
                    for f in extracted_files:
                        try:
                            zip_contents.append(f"{f}: {read_text(f)[:500]}")
                        except Exception:
                            zip_contents.append(f"{f}: [binary file]")
                    parts.append("ZIP CONTENTS:\n" + "\n".join(zip_contents))
                    data["zip_files"] = extracted_files
                except Exception as zip_e:
                    parts.append(f"ZIP ERROR ({href}): {zip_e}")

            elif href.endswith(".b64") or "base64" in href.lower():
                # Base64 encoded file - decode
                try:
                    decoded = decode_base64(content.strip())
                    parts.append(f"BASE64 DECODED:\n{decoded}")
                    data["base64_decoded"] = decoded
                except Exception:
                    parts.append(f"BASE64 FILE ({href}): {content[:500]}")

            else:
                parts.append(f"FILE ({href}):\n{content[:2000]}")

        except Exception as e:
            parts.append(f"FILE ERROR ({href}): {e}")

    # Links
    if scraped.get("links"):
        links_text = ", ".join([link["href"] for link in scraped["links"][:5]])
        parts.append(f"LINKS: {links_text}")

    return {
        "context": "\n\n".join(parts),
        "data": data,
    }
