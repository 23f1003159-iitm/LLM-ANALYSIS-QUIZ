"""Scrape additional URLs mentioned in questions."""
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import error, info, success
from tools.core.browser import get_page


async def scrape_url(url: str, base_url: str = None) -> dict:
    """
    Scrape a URL and extract its content.
    
    Args:
        url: URL to scrape (can be relative)
        base_url: Base URL for resolving relative URLs
    
    Returns:
        dict with success, text, data found
    """
    # Make absolute URL if relative
    if base_url and not url.startswith("http"):
        url = urljoin(base_url, url)
    
    info("scraper", f"scraping {url[:60]}")
    
    try:
        result = await get_page(url)
        
        text = result.get("text", "")
        
        # Extract key data from scraped page
        extracted = {
            "text": text,
            "links": result.get("links", {}),
            "url_params": result.get("url_params", {}),
        }
        
        # Look for common data patterns in text
        import re
        
        # Secret codes
        secret_match = re.search(r'secret\s*(?:code|:)?\s*(?:is\s*)?(\d+)', text, re.IGNORECASE)
        if secret_match:
            extracted["secret_code"] = secret_match.group(1)
        
        # Numbers
        numbers = re.findall(r'\b\d{4,}\b', text)
        if numbers:
            extracted["numbers"] = numbers
        
        # Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            extracted["email"] = email_match.group(0)
        
        success("scraper", f"got {len(text)} chars from scraped page")
        
        return {
            "success": True,
            "url": url,
            "extracted": extracted,
            "error": ""
        }
    except Exception as e:
        error("scraper", str(e))
        return {"success": False, "url": url, "extracted": {}, "error": str(e)}


async def scrape_all(urls: list, base_url: str = None) -> list:
    """
    Scrape multiple URLs.
    
    Args:
        urls: List of URLs to scrape
        base_url: Base URL for resolving relative URLs
    
    Returns:
        List of scrape results
    """
    import asyncio
    
    tasks = [scrape_url(url, base_url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return [r if isinstance(r, dict) else {"success": False, "error": str(r)} for r in results]
