"""Core Scraper - Universal web scraper for quiz URLs.

This module provides the scraping functionality to extract all relevant
data from quiz pages including text, audio, files, links, and parameters.
"""

from urllib.parse import urljoin

from helpers import extract_params, load_page, parse_html
from logs.logger import get_logger

logger = get_logger("scraper")


async def scrape(url: str) -> dict:
    """Scrape all data from a quiz URL.

    Loads the page using a headless browser, extracts all media and links,
    and parses parameters from the text content.

    Args:
        url: The quiz URL to scrape.

    Returns:
        dict: Scraped data containing:
            - url (str): Original URL
            - text (str): Page text content
            - html (str): Raw HTML
            - audio (list): List of audio URLs (absolute)
            - files (list): List of file dicts with href and text
            - links (list): List of link dicts with href and text
            - params (dict): Extracted parameters (cutoff, email, etc.)

    Example:
        >>> scraped = await scrape("https://quiz.com/q1")
        >>> print(scraped['params'])
        {'cutoff': 64239, 'email': 'user@example.com'}
    """
    logger.debug(f"Loading page: {url}")
    # Load page with browser
    page = await load_page(url)

    logger.debug("Parsing HTML for media and links")
    # Parse HTML for media/files
    parsed = parse_html(page["html"])

    # Extract parameters from text
    params = extract_params(page["text"])
    if params:
        logger.debug(f"Extracted parameters: {params}")

    # Resolve relative URLs to absolute
    audio = [urljoin(url, a) for a in parsed["audio"]]
    files = [{"href": urljoin(url, f["href"]), "text": f["text"]} for f in parsed["files"]]
    links = [{"href": urljoin(url, link["href"]), "text": link["text"]} for link in parsed["links"]]

    logger.debug(f"Scraped: {len(audio)} audio, {len(files)} files, {len(links)} links")

    return {
        "url": url,
        "text": page["text"],
        "html": page["html"],
        "audio": audio,
        "files": files,
        "links": links,
        "params": params,
    }
