"""Dynamic image analysis - LLM creates optimal vision prompt for each image."""
import base64
import os
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import error, info, success
from llm import call
from tools.helper.paths import get_session_dir

load_dotenv()

_API_KEY = os.getenv("NVIDIA_API_KEY")
_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
_MODEL = "meta/llama-3.2-90b-vision-instruct"


async def extract(image_path: str, prompt: str | None = None, quiz_url: str | None = None) -> dict:
    """
    Fully dynamic image analysis - LLM creates optimal vision prompt.
    
    Args:
        image_path: Path to image
        prompt: Optional custom prompt (if None, generates dynamic)
        quiz_url: Optional quiz URL to save results
    
    Returns:
        dict with success, text, error
    """
    path = Path(image_path)
    if not path.exists():
        error("vision", f"file not found: {path}")
        return {"success": False, "text": "", "error": "file not found"}
    
    # Step 1: Generate optimal vision prompt if not provided
    if prompt is None:
        info("vision", f"creating dynamic vision prompt for {path.name}")
        
        # Analyze image context
        is_screenshot = "screenshot" in path.name.lower()
        is_chart = any(word in path.name.lower() for word in ["chart", "graph", "plot"])
        is_document = any(word in path.name.lower() for word in ["doc", "pdf", "page"])
        
        context_hint = "screenshot of quiz interface" if is_screenshot else \
                      "data visualization or chart" if is_chart else \
                      "document or text image" if is_document else \
                      "quiz-related image"
        
        # LLM creates optimal prompt for THIS specific image
        prompt_generation = f"""Create the PERFECT vision analysis prompt for: {context_hint}

This image is part of a quiz. What should the vision AI extract?

Consider:
- What information is critical? (questions, numbers, data, instructions, URLs)
- What details matter? (exact wording, specific values, formatting)
- What should NOT be missed?

Write a precise, comprehensive vision prompt (2-3 sentences):"""
        
        generated_prompt = await call(prompt_generation, task="fast")
        
        if generated_prompt:
            prompt = generated_prompt.strip()
            info("vision", f"dynamic prompt: {prompt[:80]}...")
        else:
            # Fallback
            prompt = "Extract ALL text, questions, instructions, data, numbers, and URLs from this image. Be thorough and precise - don't miss any details."
    
    info("vision", f"analyzing {path.name}")
    
    b64 = base64.b64encode(path.read_bytes()).decode()
    mime = {".png": "image/png", ".jpg": "image/jpeg"}.get(path.suffix.lower(), "image/png")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _API_URL,
                headers={"Authorization": f"Bearer {_API_KEY}"},
                json={
                    "model": _MODEL,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ],
                    }],
                    "max_tokens": 2048,
                },
                timeout=120,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            
            if quiz_url:
                session_dir = get_session_dir(quiz_url)
                result_file = session_dir / f"{path.stem}_vision.txt"
                result_file.write_text(text)
                info("vision", f"saved to {result_file.name}")
            
            success("vision", f"got {len(text)} chars")
            return {"success": True, "text": text, "error": ""}
    except httpx.HTTPError as e:
        error("vision", str(e))
        return {"success": False, "text": "", "error": str(e)}
