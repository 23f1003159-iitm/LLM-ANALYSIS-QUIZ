"""Make API calls with custom headers."""
import sys
import json
from pathlib import Path
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import error, info, success


async def call_api(
    url: str,
    method: str = "GET",
    headers: dict = None,
    data: dict = None,
    timeout: int = 30
) -> dict:
    """
    Make an API call with custom headers.
    
    Args:
        url: API endpoint URL
        method: HTTP method (GET, POST, PUT, DELETE)
        headers: Custom headers dict
        data: Request body for POST/PUT
        timeout: Request timeout in seconds
    
    Returns:
        dict with success, response, status_code
    """
    info("api", f"{method} {url[:60]}")
    
    headers = headers or {}
    
    try:
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, timeout=timeout)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == "PUT":
                resp = await client.put(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == "DELETE":
                resp = await client.delete(url, headers=headers, timeout=timeout)
            else:
                return {"success": False, "response": None, "error": f"Unknown method: {method}"}
            
            # Try to parse as JSON
            try:
                response_data = resp.json()
            except:
                response_data = resp.text
            
            success("api", f"status {resp.status_code}, got response")
            
            return {
                "success": resp.status_code < 400,
                "response": response_data,
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "error": "" if resp.status_code < 400 else f"HTTP {resp.status_code}"
            }
    except httpx.TimeoutException:
        error("api", "timeout")
        return {"success": False, "response": None, "status_code": 0, "error": "timeout"}
    except Exception as e:
        error("api", str(e))
        return {"success": False, "response": None, "status_code": 0, "error": str(e)}


async def submit_answer(submit_url: str, payload: dict) -> dict:
    """
    Submit answer to quiz endpoint.
    
    Args:
        submit_url: The /submit endpoint
        payload: JSON payload with email, secret, url, answer
    
    Returns:
        dict with success, response
    """
    info("submit", f"posting to {submit_url}")
    
    result = await call_api(
        url=submit_url,
        method="POST",
        headers={"Content-Type": "application/json"},
        data=payload
    )
    
    if result["success"]:
        success("submit", f"submitted! response: {result['response']}")
    else:
        error("submit", f"failed: {result['error']}")
    
    return result
