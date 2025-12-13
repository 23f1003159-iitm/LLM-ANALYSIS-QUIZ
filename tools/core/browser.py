"""Load web pages and extract data - NO file saving, just extraction + logging."""

import sys
import re
from pathlib import Path
from urllib.parse import urljoin
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import error, info, success


async def get_page(url: str, timeout: int = 60000) -> dict:
    """
    Open a webpage and extract EVERYTHING useful from it.
    Handles JS-rendered content, extracts all text, links, media.
    """
    info("browser", f"loading {url[:60]}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            # Wait extra for JS to fully render
            await page.wait_for_timeout(3000)
        except Exception as e:
            error("browser", f"page load error: {str(e)[:100]}")
        
        # ===== EXTRACT ALL TEXT (clean, no labels) =====
        text_parts = []
        
        # 1. Get page title
        title = await page.title()
        if title:
            text_parts.append(title)
        
        # 2. Get all headings (h1-h6)
        headings = await page.eval_on_selector_all(
            "h1, h2, h3, h4, h5, h6",
            "els => els.map(e => e.innerText.trim()).filter(Boolean)"
        )
        if headings:
            text_parts.extend(headings)
        
        # 3. Get all paragraphs
        paragraphs = await page.eval_on_selector_all(
            "p",
            "els => els.map(e => e.innerText.trim()).filter(Boolean)"
        )
        if paragraphs:
            text_parts.extend(paragraphs)
        
        # 4. Get pre/code blocks (JSON, code examples)
        code_blocks = await page.eval_on_selector_all(
            "pre, code",
            "els => els.map(e => e.innerText.trim()).filter(Boolean)"
        )
        if code_blocks:
            text_parts.extend(code_blocks)
        
        # 5. Get list items (ul/ol)
        list_items = await page.eval_on_selector_all(
            "li",
            "els => els.map(e => e.innerText.trim()).filter(Boolean)"
        )
        if list_items:
            text_parts.extend(list_items[:20])  # Limit
        
        # 6. Get divs with text (often contains dynamic content)
        div_text = await page.eval_on_selector_all(
            "div",
            """els => els.map(e => {
                const text = e.innerText.trim();
                if (text.length > 10 && text.length < 2000) return text;
                return null;
            }).filter(Boolean)"""
        )
        # Deduplicate div text
        seen = set()
        unique_divs = []
        for t in div_text:
            if t not in seen and len(t) > 20:
                seen.add(t)
                unique_divs.append(t)
        if unique_divs:
            text_parts.extend(unique_divs[:10])
        
        # 7. Get full body text as master reference
        body_text = await page.inner_text("body")
        
        # Combine structured parts - use body text as fallback
        structured_text = "\n\n".join(text_parts)
        if len(body_text) > len(structured_text):
            full_text = body_text  # Just use clean body text
        else:
            full_text = structured_text if structured_text else body_text
        
        # ===== EXTRACT ALL LINKS =====
        all_links = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))"
        )
        
        # ===== EXTRACT MEDIA SOURCES =====
        audio_src = await page.eval_on_selector_all(
            "audio, audio source",
            "els => els.map(e => e.src).filter(Boolean)"
        )
        video_src = await page.eval_on_selector_all(
            "video, video source",
            "els => els.map(e => e.src).filter(Boolean)"
        )
        image_src = await page.eval_on_selector_all(
            "img[src]",
            "els => els.map(e => e.src).filter(Boolean)"
        )
        
        # ===== GET FULL HTML =====
        html = await page.content()
        
        await browser.close()
    
    # ===== CATEGORIZE LINKS =====
    links = {
        "audio": list(set(audio_src)),
        "video": list(set(video_src)),
        "image": [img for img in set(image_src) if not img.startswith("data:")],
        "pdf": [],
        "csv": [],
        "json": [],
        "excel": [],
        "other": [],
        "scrape": [],  # Links that need to be followed/scraped
        "submit": [],  # Submit URLs
    }
    
    for link in all_links:
        href = link.get("href", "")
        text = link.get("text", "").lower()
        h = href.lower()
        
        if not href or href.startswith("javascript:") or href.startswith("#"):
            continue
        
        # Make absolute URL
        if not href.startswith("http"):
            href = urljoin(url, href)
            h = href.lower()
        
        # Categorize by extension
        if h.endswith((".mp3", ".wav", ".m4a", ".opus", ".ogg")):
            links["audio"].append(href)
        elif h.endswith((".mp4", ".webm", ".avi")):
            links["video"].append(href)
        elif h.endswith(".pdf"):
            links["pdf"].append(href)
        elif h.endswith(".csv"):
            links["csv"].append(href)
        elif h.endswith(".json"):
            links["json"].append(href)
        elif h.endswith((".xlsx", ".xls")):
            links["excel"].append(href)
        elif h.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            links["image"].append(href)
        else:
            links["other"].append(href)
        
        # Detect submit URLs
        if "submit" in h or "submit" in text:
            links["submit"].append(href)
        
        # Detect scrape links (keywords in text or URL)
        scrape_keywords = ["scrape", "data", "secret", "fetch", "get"]
        if any(kw in text for kw in scrape_keywords) or any(kw in h for kw in scrape_keywords):
            if "submit" not in h:  # Don't add submit to scrape
                links["scrape"].append(href)
    
    # Also find submit URL from page text
    submit_match = re.search(r'(?:POST|submit)[^"\']*?(https?://[^\s<>"\']+/submit)', full_text, re.IGNORECASE)
    if submit_match:
        links["submit"].append(submit_match.group(1))
    
    # Deduplicate all
    for key in links:
        links[key] = list(set(links[key]))
    
    # Remove empty categories
    links = {k: v for k, v in links.items() if v}
    
    # ===== EXTRACT DATA FROM URL (only what's actually in URL) =====
    email_match = re.search(r'[?&]email=([^&\s]+)', url)
    email_param = email_match.group(1) if email_match else None
    
    # Extract all key-value pairs from URL
    url_params = {}
    for match in re.finditer(r'[?&]([^=&]+)=([^&\s]+)', url):
        url_params[match.group(1)] = match.group(2)
    
    total_links = sum(len(v) for v in links.values())
    success("browser", f"got {len(full_text)} chars, {total_links} links")
    
    result = {
        "text": full_text,
        "links": links,
        "html": html,
        "url": url,
        "url_params": url_params,
    }
    
    return result
