"""Helper - Web operations (HTTP requests and browser automation).

Provides functions for HTTP requests and headless browser automation
for loading dynamic web pages.
"""

import contextlib

import httpx
from playwright.async_api import async_playwright


async def fetch_url(url: str) -> str:
    """Fetch URL content via HTTP GET.

    Args:
        url: URL to fetch.

    Returns:
        str: Response text content.

    Raises:
        httpx.HTTPError: If request fails.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60)
        response.raise_for_status()
        return response.text


async def post_json(url: str, data: dict) -> dict:
    """POST JSON data to URL.

    Args:
        url: URL to POST to.
        data: Dictionary to send as JSON.

    Returns:
        dict: JSON response parsed as dictionary.

    Raises:
        httpx.HTTPError: If request fails.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, timeout=60)
        response.raise_for_status()
        return response.json()


async def load_page(url: str) -> dict:
    """Load page using headless browser.

    Uses Playwright to load the page, wait for network idle,
    and extract both HTML and visible text.

    Args:
        url: URL to load.

    Returns:
        dict: Page data containing:
            - html (str): Full HTML content
            - text (str): Visible text from body

    Example:
        >>> page = await load_page("https://example.com")
        >>> print(page['text'][:100])
        Example Domain
        This domain is for use in...

    Note:
        Waits up to 10 seconds for networkidle state, but continues
        if timeout occurs (some pages never reach networkidle).
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # Wait for network idle (best effort, don't fail if timeout)
        with contextlib.suppress(Exception):
            await page.wait_for_load_state("networkidle", timeout=10000)

        html = await page.content()
        text = await page.evaluate("() => document.body.innerText")
        await browser.close()

        return {"html": html, "text": text}
