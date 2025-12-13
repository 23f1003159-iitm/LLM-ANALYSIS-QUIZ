"""
LLM Analysis Quiz - API Server
==============================
HTTP endpoint to receive quiz tasks and solve them automatically.

Usage:
    uv run uvicorn server:app --host 0.0.0.0 --port 8000
"""
import os
import sys
import asyncio
import time
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx

load_dotenv()

from log import header, info, success, error, divider, warn
from agent import solve
from tools.helper.api_caller import submit_answer
from tools.helper.paths import get_session_dir

# Config from .env
SECRET_KEY = os.getenv("SECRET_KEY", "")
EMAIL = os.getenv("EMAIL", "")

# Quiz timeout (3 minutes = 180 seconds, use 170 for safety margin)
QUIZ_TIMEOUT = 170

app = FastAPI(title="LLM Quiz Solver")


@app.post("/")
async def handle_quiz(request: Request):
    """
    Main endpoint to receive quiz tasks.
    
    Expected payload:
    {
        "email": "student email",
        "secret": "student secret",
        "url": "quiz URL to solve"
    }
    
    Returns:
        HTTP 200: Valid request (processing started)
        HTTP 400: Invalid JSON
        HTTP 403: Invalid secret
    """
    header("Incoming Quiz Request")
    
    # Parse JSON
    try:
        payload = await request.json()
    except Exception as e:
        error("server", f"invalid JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Validate required fields
    email = payload.get("email")
    secret = payload.get("secret")
    quiz_url = payload.get("url")
    
    if not all([email, secret, quiz_url]):
        error("server", "missing required fields")
        raise HTTPException(status_code=400, detail="Missing required fields: email, secret, url")
    
    # Verify secret
    if secret != SECRET_KEY:
        error("server", f"invalid secret from {email}")
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    success("server", f"valid request from {email}")
    info("server", f"quiz URL: {quiz_url}")
    
    # Process quiz in background (respond immediately)
    asyncio.create_task(process_quiz(email, secret, quiz_url))
    
    return JSONResponse(
        status_code=200,
        content={"status": "processing", "url": quiz_url}
    )


async def process_quiz(email: str, secret: str, quiz_url: str):
    """
    Process a quiz URL - solve and submit answer.
    Handles the chain of quiz URLs with 3-minute timeout.
    Retries on wrong answer before moving to next URL.
    """
    start_time = time.time()
    current_url = quiz_url
    max_retries_per_question = 2
    
    # Statistics tracking
    stats = {
        "total_questions": 0,
        "correct": 0,
        "wrong": 0,
        "skipped": 0,
        "questions": []  # Track each question's result
    }
    
    while current_url:
        # Check 3-minute timeout
        elapsed = time.time() - start_time
        if elapsed >= QUIZ_TIMEOUT:
            warn("server", f"timeout reached ({elapsed:.1f}s), stopping")
            break
        
        remaining_time = QUIZ_TIMEOUT - elapsed
        info("server", f"processing: {current_url} (remaining: {remaining_time:.0f}s)")
        
        for attempt in range(max_retries_per_question):
            # Check timeout before each attempt
            if time.time() - start_time >= QUIZ_TIMEOUT:
                warn("server", "timeout reached during retry")
                return
            
            try:
                # Solve the quiz
                result = await asyncio.wait_for(
                    solve(current_url),
                    timeout=min(90, remaining_time)  # Max 90s per solve, or remaining time
                )
                
                if not result.get("success"):
                    error("server", f"failed to solve quiz (attempt {attempt + 1})")
                    continue
                
                # Build submission payload
                answer = result.get("answer")
                submit_url = result.get("submit_url")
                
                if not submit_url:
                    error("server", "no submit URL found")
                    break
                
                # Parse answer to appropriate type (handles base64, json, etc.)
                parsed_answer = parse_answer(answer, result.get("answer_type", "text"), result)
                
                submission = {
                    "email": email,
                    "secret": secret,
                    "url": current_url,
                    "answer": parsed_answer
                }
                
                # Check payload size (must be under 1MB)
                import json as json_lib
                payload_str = json_lib.dumps(submission)
                payload_size = len(payload_str.encode('utf-8'))
                if payload_size > 1_000_000:  # 1MB limit
                    warn("server", f"payload too large: {payload_size} bytes, truncating")
                    # If answer is base64, it might be too large - skip this answer
                    error("server", "answer exceeds 1MB limit")
                    continue
                
                info("server", f"submitting answer ({payload_size} bytes): {str(parsed_answer)[:100]}")
                
                # Submit answer
                submit_result = await submit_answer(submit_url, submission)
                
                if submit_result.get("success"):
                    response = submit_result.get("response", {})
                    
                    if isinstance(response, dict):
                        correct = response.get("correct", False)
                        next_url = response.get("url")
                        reason = response.get("reason")
                        
                        if correct:
                            stats["correct"] += 1
                            stats["total_questions"] += 1
                            stats["questions"].append({"url": current_url, "result": "correct"})
                            success("server", f"✓ correct! [{stats['correct']}/{stats['total_questions']}] next: {next_url}")
                            current_url = next_url  # Move to next quiz
                            break
                        else:
                            warn("server", f"✗ wrong answer: {reason}")
                            # Retry on wrong answer (stay in loop)
                            if attempt < max_retries_per_question - 1:
                                info("server", f"retrying... (attempt {attempt + 2})")
                                continue
                            # After all retries, check if we got a next URL to skip to
                            elif next_url:
                                stats["wrong"] += 1
                                stats["total_questions"] += 1
                                stats["questions"].append({"url": current_url, "result": "wrong", "reason": reason})
                                info("server", f"skipping to next URL: {next_url}")
                                current_url = next_url
                                break
                            else:
                                stats["wrong"] += 1
                                stats["total_questions"] += 1
                                stats["questions"].append({"url": current_url, "result": "wrong", "reason": reason})
                    else:
                        info("server", f"response: {response}")
                        current_url = None
                        break
                else:
                    error("server", f"submit failed: {submit_result.get('error')}")
                    
            except asyncio.TimeoutError:
                error("server", "solve timeout, moving on")
                break
            except Exception as e:
                error("server", f"error: {str(e)[:100]}")
        
        else:
            # All retries exhausted without success or next_url
            error("server", "max retries reached without next URL")
            current_url = None
    
    divider()
    elapsed = time.time() - start_time
    
    # Print final statistics
    header("Quiz Statistics")
    print(f"  Total Questions: {stats['total_questions']}")
    print(f"  ✓ Correct: {stats['correct']}")
    print(f"  ✗ Wrong: {stats['wrong']}")
    if stats['total_questions'] > 0:
        accuracy = (stats['correct'] / stats['total_questions']) * 100
        print(f"  Accuracy: {accuracy:.1f}%")
    print(f"  Time: {elapsed:.1f}s")
    
    # Save stats to file
    import json
    stats_file = Path("quiz_stats.json")
    stats["elapsed_time"] = elapsed
    stats["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    stats_file.write_text(json.dumps(stats, indent=2))
    info("server", f"stats saved to {stats_file}")
    
    success("server", f"quiz complete: {stats['correct']}/{stats['total_questions']} correct in {elapsed:.1f}s")


def parse_answer(answer, answer_type: str, result: dict = None):
    """
    Parse answer to appropriate type.
    Handles: number, boolean, text, json, base64 (for images/files)
    """
    if answer is None:
        return None
    
    # Handle number type
    if answer_type == "number":
        try:
            if "." in str(answer):
                return float(answer)
            return int(answer)
        except (ValueError, TypeError):
            return answer
    
    # Handle boolean type
    elif answer_type == "boolean":
        if isinstance(answer, bool):
            return answer
        lower = str(answer).lower()
        if lower in ("true", "1", "yes"):
            return True
        elif lower in ("false", "0", "no"):
            return False
        return answer
    
    # Handle JSON type
    elif answer_type == "json":
        import json
        if isinstance(answer, (dict, list)):
            return answer
        try:
            return json.loads(answer)
        except:
            return answer
    
    # Handle base64/image type - for chart or file answers
    elif answer_type in ("base64", "image", "file", "chart"):
        return handle_file_answer(answer, result)
    
    # Default: return as-is
    return answer


def handle_file_answer(answer, result: dict = None):
    """
    Handle file-based answers (charts, images, etc.)
    Returns base64 data URI.
    """
    if result is None:
        return answer
    
    # Check if we have a generated chart
    session_dir = None
    if result.get("url"):
        session_dir = get_session_dir(result["url"])
    
    # If answer is already a base64 data URI, return it
    if isinstance(answer, str) and answer.startswith("data:"):
        return answer
    
    # If answer is a file path, convert to base64
    if isinstance(answer, str):
        path = Path(answer)
        if path.exists() and path.is_file():
            return file_to_base64(path)
        
        # Check in session directory
        if session_dir:
            session_path = session_dir / answer
            if session_path.exists():
                return file_to_base64(session_path)
    
    # Check for chart in session
    if session_dir:
        chart_path = session_dir / "chart.png"
        if chart_path.exists():
            return file_to_base64(chart_path)
    
    return answer


def file_to_base64(filepath: Path) -> str:
    """Convert file to base64 data URI."""
    data = filepath.read_bytes()
    b64 = base64.b64encode(data).decode()
    
    # Determine MIME type
    ext = filepath.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".csv": "text/csv",
        ".json": "application/json",
    }
    mime = mime_types.get(ext, "application/octet-stream")
    
    return f"data:{mime};base64,{b64}"


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "email": EMAIL}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
