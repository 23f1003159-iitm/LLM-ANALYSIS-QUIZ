"""
Ultimate Data Collector for Quiz URLs
=====================================
Single module that collects ALL data from a quiz URL and saves to session folder.
Uses browser.py for extraction, saves everything cleanly.
"""
import sys
import json
import asyncio
from pathlib import Path
import httpx
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import error, info, success
from tools.helper.paths import get_session_dir, get_screenshot_path
from tools.core.browser import get_page


async def collect_all(quiz_url: str) -> dict:
    """
    Ultimate data collector - fetches page, downloads files, saves everything.
    
    Args:
        quiz_url: The quiz URL to collect data from
    
    Returns:
        dict with all collected data and file paths
    """
    info("collector", f"collecting data from {quiz_url[:50]}")
    
    session_dir = get_session_dir(quiz_url)
    
    # 1. Get page data using browser.py
    page_data = await get_page(quiz_url)
    
    # 2. Save page text
    page_text_file = session_dir / "page_text.txt"
    page_text_file.write_text(page_data["text"])
    
    # 3. Save clean browser data JSON
    links = page_data.get("links", {})
    simple_links = {}
    for key in ["audio", "csv", "pdf", "scrape", "submit", "json", "excel"]:
        if links.get(key):
            val = links[key]
            simple_links[key] = val[0] if len(val) == 1 else val
    
    browser_json = session_dir / "browser_data.json"
    json_data = {
        "url": quiz_url,
        "params": page_data.get("url_params") or None,
        "links": simple_links or None,
    }
    json_data = {k: v for k, v in json_data.items() if v is not None}
    browser_json.write_text(json.dumps(json_data, indent=2, ensure_ascii=False))
    
    success("collector", f"saved to {session_dir.name}/")
    
    return {
        "session_dir": str(session_dir),
        "page_text": page_data["text"],
        "links": links,
        "url_params": page_data.get("url_params", {}),
        "files": {
            "page_text": str(page_text_file),
            "browser_data": str(browser_json),
        }
    }


async def download_file(url: str, quiz_url: str) -> dict:
    """Download file and save to session folder."""
    session_dir = get_session_dir(quiz_url)
    filename = url.split("/")[-1].split("?")[0]
    filepath = session_dir / filename
    
    info("download", f"getting {filename}")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=60)
            filepath.write_bytes(resp.content)
            success("download", f"saved {filepath.name} ({len(resp.content)} bytes)")
            return {"success": True, "path": str(filepath), "size": len(resp.content)}
    except Exception as e:
        error("download", str(e)[:50])
        return {"success": False, "error": str(e)}


async def download_all(links: dict, quiz_url: str) -> dict:
    """Download all files from links dict in parallel."""
    downloaded = {
        "audio": [],
        "video": [],
        "image": [],
        "pdf": [],
        "csv": [],
        "json": [],
        "excel": [],
    }
    
    tasks = []
    categories = []
    
    for category in downloaded:
        if category in links:
            urls = links[category]
            if isinstance(urls, str):
                urls = [urls]
            for file_url in urls:
                tasks.append(download_file(file_url, quiz_url))
                categories.append(category)
    
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for category, result in zip(categories, results):
            if isinstance(result, dict) and result.get("success"):
                downloaded[category].append(result["path"])
    
    return {k: v for k, v in downloaded.items() if v}


async def take_screenshot(url: str, quiz_url: str = None) -> str:
    """Take screenshot and save to session folder."""
    quiz = quiz_url or url
    filepath = get_screenshot_path(quiz)
    
    info("screenshot", f"capturing {url[:40]}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(filepath), full_page=True)
        await browser.close()
    
    success("screenshot", f"saved {filepath.name}")
    return str(filepath)


async def scrape_url(url: str, base_url: str = None) -> dict:
    """Scrape a linked URL and extract its content."""
    from urllib.parse import urljoin
    import re
    
    # Make absolute URL
    if base_url and not url.startswith("http"):
        url = urljoin(base_url, url)
    
    info("scraper", f"scraping {url[:50]}")
    
    try:
        page_data = await get_page(url)
        text = page_data.get("text", "")
        
        # Extract secret code if present
        secret_match = re.search(r'secret\s*(?:code|:)?\s*(?:is\s*)?[:\s]*(\d+)', text, re.IGNORECASE)
        secret = secret_match.group(1) if secret_match else None
        
        # Also look for standalone numbers
        if not secret:
            numbers = re.findall(r'\b\d{4,6}\b', text)
            if len(numbers) == 1:
                secret = numbers[0]
        
        result = {
            "success": True,
            "url": url,
            "text": text,
            "secret": secret,
        }
        
        if secret:
            success("scraper", f"found secret: {secret}")
        
        return result
    except Exception as e:
        error("scraper", str(e)[:50])
        return {"success": False, "url": url, "error": str(e)}
