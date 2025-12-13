"""
LLM Quiz Solver - SIMPLIFIED
============================
Single-file server + solver. One model, minimal LLM calls.

Usage:
    uv run python simple_server.py
"""
import os
import sys
import asyncio
import time
import json
import hashlib
import base64
from pathlib import Path
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
from playwright.async_api import async_playwright

load_dotenv()

# Config
SECRET_KEY = os.getenv("SECRET_KEY", "")
EMAIL = os.getenv("EMAIL", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Timeout: 3 minutes with safety margin
QUIZ_TIMEOUT = 170

app = FastAPI(title="LLM Quiz Solver - Simplified")

# ============================================================
# LOGGING (inline for simplicity)
# ============================================================
def log(icon: str, tag: str, msg: str):
    t = time.strftime("%H:%M:%S")
    print(f"{t} {icon} [{tag:^10}] {msg}")

def info(tag, msg): log("●", tag, msg)
def success(tag, msg): log("✓", tag, msg)
def error(tag, msg): log("✗", tag, msg)
def warn(tag, msg): log("⚠", tag, msg)

# ============================================================
# LLM CLIENT (simplified - ONE model)
# ============================================================
async def llm_call(prompt: str, max_tokens: int = 4096) -> str | None:
    """Single LLM call using Llama 3.3 70B (more reliable for structured output)."""
    info("llm", "calling llama-3.3-70b")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {NVIDIA_API_KEY}"},
                json={
                    "model": "meta/llama-3.3-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            if "choices" not in data or not data["choices"]:
                error("llm", f"no choices in response: {str(data)[:200]}")
                return None
            result = data["choices"][0]["message"]["content"]
            if result:
                success("llm", f"got {len(result)} chars")
            else:
                warn("llm", "empty content in response")
            return result
    except httpx.HTTPStatusError as e:
        error("llm", f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        error("llm", f"error: {type(e).__name__}: {str(e)[:100]}")
        return None


async def vision_call(image_path: str, prompt: str) -> str | None:
    """Vision API call."""
    info("vision", f"analyzing {Path(image_path).name}")
    try:
        img_data = Path(image_path).read_bytes()
        b64 = base64.b64encode(img_data).decode()
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {NVIDIA_API_KEY}"},
                json={
                    "model": "meta/llama-3.2-90b-vision-instruct",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ],
                    }],
                    "max_tokens": 2048,
                },
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"]
            success("vision", f"got {len(result)} chars")
            return result
    except Exception as e:
        error("vision", str(e)[:100])
        return None


# ============================================================
# BROWSER (simplified)
# ============================================================
async def load_page(url: str) -> tuple[str, str, list]:
    """Load page, take screenshot, return (text, screenshot_path, links)."""
    info("browser", f"loading {url[:60]}")
    
    session_id = hashlib.md5(url.encode()).hexdigest()[:8]
    session_dir = Path(f"data/sessions/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = session_dir / "screenshot.png"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(1)  # Wait for JS rendering
        
        # Get text content
        text = await page.evaluate("() => document.body.innerText")
        
        # Take screenshot
        await page.screenshot(path=str(screenshot_path))
        
        # Get links
        links = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({href: a.href, text: a.innerText.trim()}))
                .filter(l => l.href && !l.href.startsWith('javascript:'))
        }""")
        
        await browser.close()
    
    success("browser", f"got {len(text)} chars, {len(links)} links")
    return text, str(screenshot_path), links


async def fetch_url(url: str) -> str:
    """Fetch a URL using browser for JavaScript rendering."""
    info("fetch", f"getting {url[:60]}")
    try:
        # First try simple HTTP fetch
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10, follow_redirects=True)
            resp.raise_for_status()
            text = resp.text
            
            # Check if it's JavaScript-rendered content
            if "<script" in text.lower() and len(text) < 500:
                # Need to use browser
                info("fetch", "JS content detected, using browser")
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(url, wait_until="networkidle", timeout=15000)
                    await asyncio.sleep(0.5)
                    text = await page.evaluate("() => document.body.innerText")
                    await browser.close()
            
            success("fetch", f"got {len(text)} chars")
            return text
    except Exception as e:
        error("fetch", str(e)[:100])
        return ""


# ============================================================
# SOLVER (simplified - ONE LLM call to solve)
# ============================================================
async def solve_quiz(url: str, page_text: str, screenshot_path: str, links: list) -> dict:
    """Solve quiz with ONE combined LLM call."""
    info("solver", "solving quiz")
    
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    
    # Step 1: Vision analysis (if screenshot exists)
    vision_text = ""
    if Path(screenshot_path).exists():
        vision_prompt = """Extract ALL text and information from this quiz screenshot:
1. The main question being asked
2. Any data, numbers, or values shown
3. Instructions for answering
4. The submit URL or endpoint
5. Any file download links or URLs to scrape

Be thorough - capture everything visible."""
        
        vision_text = await vision_call(screenshot_path, vision_prompt) or ""
    
    # Step 2: Detect scraping tasks and fetch additional data
    combined_text = f"{page_text} {vision_text}"
    scraped_data = ""
    
    import re
    
    # First, try to find ALL URLs in the combined text (page + vision)
    url_patterns = [
        r'https?://[^\s\"\'\<\>]+',  # Full URLs
        r'/project2-reevals[/\w\.-]+',  # Relative paths
    ]
    
    found_urls = []
    for pattern in url_patterns:
        found_urls.extend(re.findall(pattern, combined_text, re.IGNORECASE))
    
    # Also add all link hrefs
    for link in links:
        href = link.get("href", "")
        if href and not href.startswith("javascript:"):
            found_urls.append(href)
    
    # Filter to data-like URLs (not the main page itself)
    data_extensions = ['.json', '.csv', '.txt', '.xml', '.sql', '.log', '.data']
    data_keywords = ['data', 'api', 'secret', 'code', 'endpoint', 'tweets', 'users', 'products', 'sales']
    
    for url in found_urls:
        # Skip if it's the main quiz page
        if 'project2-reevals?' in url or url.endswith('/project2-reevals'):
            continue
        
        # Convert relative URLs
        if url.startswith('/'):
            url = urljoin(base_url, url)
        
        # Check if it looks like a data URL
        is_data_url = any(ext in url.lower() for ext in data_extensions) or \
                      any(kw in url.lower() for kw in data_keywords)
        
        if is_data_url:
            info("solver", f"fetching data URL: {url[:60]}")
            scraped_data = await fetch_url(url)
            if scraped_data and len(scraped_data) > 10:
                break
    
    # If still no data, try all links just in case
    if not scraped_data:
        for link in links:
            href = link.get("href", "")
            if href and '/project2-reevals?' not in href:
                if not href.startswith("http"):
                    href = urljoin(base_url, href)
                info("solver", f"trying link: {href[:60]}")
                scraped_data = await fetch_url(href)
                if scraped_data and len(scraped_data) > 10:
                    break
    
    # Step 3: If scraped data looks like CSV, try to extract useful info
    data_summary = ""
    if scraped_data:
        lines = scraped_data.strip().split("\n")
        if len(lines) > 1 and "," in lines[0]:
            # CSV data - try to compute sum if numbers are present
            try:
                import csv
                from io import StringIO
                reader = csv.DictReader(StringIO(scraped_data))
                rows = list(reader)
                if rows:
                    headers = list(rows[0].keys())
                    data_summary = f"CSV with {len(rows)} rows, columns: {headers}"
                    # Try to sum numeric columns
                    for col in headers:
                        try:
                            total = sum(float(row[col]) for row in rows if row[col].replace('.','').replace('-','').isdigit())
                            if total != 0:
                                data_summary += f"\nSum of {col}: {total}"
                        except:
                            pass
                    info("solver", f"CSV parsed: {data_summary[:100]}")
            except Exception as e:
                data_summary = f"Raw data: {scraped_data[:500]}"
        else:
            data_summary = f"Raw data: {scraped_data[:1000]}"
    
    # Step 4: ONE LLM call to solve
    links_text = "\n".join([f"- {l['text']}: {l['href']}" for l in links[:10]])
    
    # Show full scraped data for secret extraction
    full_scraped = scraped_data[:3000] if scraped_data else "None"
    
    solve_prompt = f"""You are solving a quiz. Read ALL data carefully.

=== PAGE INSTRUCTIONS ===
{page_text[:1500]}

=== SCREENSHOT TEXT ===
{vision_text[:1000]}

=== DATA FROM SCRAPED URL ===
{full_scraped}

{f"Data summary: {data_summary}" if data_summary else ""}

=== LINKS ON PAGE ===
{links_text}

INSTRUCTIONS:
1. Read the question carefully from the page/screenshot
2. The answer is in the scraped data - look for:
   - A "secret" or "code" value if mentioned
   - A number to calculate (sum, count, etc.)
3. Use /submit as the submit endpoint (base: {base_url})

CRITICAL: 
- If asked for a "secret code", find the exact value in the scraped data
- If asked for a sum, use the calculated sum from the data summary above
- Return the EXACT value, not a description

Return ONLY valid JSON:
{{"question": "brief question", "answer": "THE ACTUAL VALUE", "submit_url": "{base_url}/submit"}}"""

    response = await llm_call(solve_prompt, max_tokens=2048)
    
    if not response:
        return {"success": False, "error": "LLM failed"}
    
    # Parse JSON from response using multiple methods
    import re
    
    def try_extract_json():
        # Method 1: Try to find JSON with all expected keys
        patterns = [
            r'\{[^{}]*"question"[^{}]*"answer"[^{}]*"submit_url"[^{}]*\}',
            r'\{[^{}]*"answer"[^{}]*"question"[^{}]*\}',
            r'\{[^{}]*"answer"\s*:\s*"[^"]*"[^{}]*\}',
        ]
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    continue
        
        # Method 2: Extract answer directly using regex
        answer_match = re.search(r'"answer"\s*:\s*"([^"]*)"', response)
        if answer_match:
            return {"answer": answer_match.group(1)}
        
        # Method 3: Look for answer after "answer:" text
        answer_match = re.search(r'answer[:\s]+([^\n,}]+)', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).strip().strip('"').strip("'")
            return {"answer": answer}
        
        return None
    
    result = try_extract_json()
    if result and result.get("answer"):
        # Ensure submit_url is set
        submit_url = result.get("submit_url", "")
        if submit_url and not submit_url.startswith("http"):
            submit_url = urljoin(base_url, submit_url)
        if not submit_url:
            submit_url = f"{base_url}/submit"
        result["submit_url"] = submit_url
        
        success("solver", f"answer: {str(result.get('answer'))[:50]}")
        return {"success": True, **result}
    
    error("solver", f"Could not extract answer from: {response[:200]}")
    return {"success": False, "error": "Failed to parse response"}


# ============================================================
# SUBMIT ANSWER
# ============================================================
async def submit_answer(submit_url: str, payload: dict) -> dict:
    """Submit answer to the quiz endpoint."""
    info("submit", f"posting to {submit_url[:50]}")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                submit_url,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
            success("submit", f"response: {result}")
            return {"success": True, "response": result}
    except Exception as e:
        error("submit", str(e)[:100])
        return {"success": False, "error": str(e)}


# ============================================================
# MAIN QUIZ PROCESSING
# ============================================================
async def process_quiz(email: str, secret: str, quiz_url: str):
    """Process quiz chain with timeout."""
    start_time = time.time()
    current_url = quiz_url
    
    stats = {"total": 0, "correct": 0, "wrong": 0}
    
    while current_url:
        elapsed = time.time() - start_time
        if elapsed >= QUIZ_TIMEOUT:
            warn("server", f"timeout ({elapsed:.0f}s)")
            break
        
        remaining = QUIZ_TIMEOUT - elapsed
        info("server", f"processing: {current_url[:60]} ({remaining:.0f}s left)")
        
        try:
            # Load page
            page_text, screenshot_path, links = await asyncio.wait_for(
                load_page(current_url),
                timeout=min(30, remaining)
            )
            
            # Solve
            result = await asyncio.wait_for(
                solve_quiz(current_url, page_text, screenshot_path, links),
                timeout=min(60, remaining - 30)
            )
            
            if not result.get("success"):
                error("server", f"solve failed: {result.get('error')}")
                break
            
            # Submit
            submission = {
                "email": email,
                "secret": secret,
                "url": current_url,
                "answer": result["answer"]
            }
            
            submit_result = await submit_answer(result["submit_url"], submission)
            
            if submit_result.get("success"):
                response = submit_result.get("response", {})
                stats["total"] += 1
                
                if response.get("correct"):
                    stats["correct"] += 1
                    success("server", f"✓ CORRECT [{stats['correct']}/{stats['total']}]")
                    current_url = response.get("url")
                else:
                    stats["wrong"] += 1
                    warn("server", f"✗ WRONG: {response.get('reason')}")
                    current_url = response.get("url")  # Try next if provided
            else:
                error("server", "submit failed")
                break
                
        except asyncio.TimeoutError:
            error("server", "timeout on current question")
            break
        except Exception as e:
            error("server", f"error: {str(e)[:100]}")
            break
    
    # Final stats
    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"  QUIZ COMPLETE")
    print(f"  Total: {stats['total']} | Correct: {stats['correct']} | Wrong: {stats['wrong']}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"{'='*50}\n")


# ============================================================
# API ENDPOINT
# ============================================================
@app.post("/")
async def handle_quiz(request: Request):
    """Main endpoint for quiz requests."""
    print(f"\n{'='*50}")
    print("  INCOMING QUIZ REQUEST")
    print(f"{'='*50}")
    
    try:
        payload = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    email = payload.get("email")
    secret = payload.get("secret")
    quiz_url = payload.get("url")
    
    if not all([email, secret, quiz_url]):
        raise HTTPException(status_code=400, detail="Missing fields")
    
    if secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    success("server", f"valid request: {quiz_url[:50]}")
    
    # Process in background
    asyncio.create_task(process_quiz(email, secret, quiz_url))
    
    return JSONResponse({"status": "processing", "url": quiz_url})


@app.get("/health")
async def health():
    return {"status": "ok", "email": EMAIL}


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting Simplified Quiz Solver...")
    print(f"📧 Email: {EMAIL}")
    print(f"🔑 Secret: {'*' * len(SECRET_KEY)}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
