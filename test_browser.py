"""Test browser.py with multiple URLs to see what it fetches."""
import asyncio
import json
from tools.core.browser import get_page


async def test_browser():
    urls = [
        "https://tds-llm-analysis.s-anand.net/demo",
        "https://tds-llm-analysis.s-anand.net/demo-scrape?email=your-email@example.com&id=64156",
        "https://tds-llm-analysis.s-anand.net/demo-audio?email=your-email@example.com&id=64156",
    ]
    
    for url in urls:
        print("\n" + "=" * 80)
        print(f"URL: {url}")
        print("=" * 80)
        
        result = await get_page(url)
        
        print("\n--- TEXT EXTRACTED ---")
        print(result["text"][:2000])
        
        print("\n--- LINKS FOUND ---")
        print(json.dumps(result["links"], indent=2))
        
        print("\n--- URL PARAMS ---")
        print(json.dumps(result.get("url_params", {}), indent=2))
        
        print("\n" + "-" * 80)


if __name__ == "__main__":
    asyncio.run(test_browser())
