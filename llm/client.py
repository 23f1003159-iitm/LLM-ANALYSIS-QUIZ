"""Async LLM client - parallel API calls."""
import base64
import os
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).parent.parent))
from log import error, info, success
load_dotenv()
_API_KEY = os.getenv("NVIDIA_API_KEY")
_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODELS = {
    "reason": "deepseek-ai/deepseek-r1",
    "code": "qwen/qwen2.5-coder-32b-instruct",
    "vision": "meta/llama-3.2-90b-vision-instruct",
    "fast": "meta/llama-3.1-8b-instruct",
    "prompt": "meta/llama-3.3-70b-instruct",
}
async def call(prompt: str, task: str = "reason") -> str | None:
    """Ask AI (async) - can call multiple at once!"""
    model = MODELS.get(task, MODELS["reason"])
    info("llm", f"asking {model.split('/')[-1]}")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _API_URL,
                headers={"Authorization": f"Bearer {_API_KEY}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                },
                timeout=120,
            )
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"]
            if result:
                success("llm", f"got {len(result)} chars")
                return result
            else:
                error("llm", "empty response")
                return None
    except httpx.HTTPError as e:
        error("llm", str(e))
        return None

async def see(image_path: str, prompt: str = "Describe this image") -> str | None:
    """Vision API (async)."""
    path = Path(image_path)
    info("vision", f"looking at {path.name}")
    
    b64 = base64.b64encode(path.read_bytes()).decode()
    mime = {".png": "image/png", ".jpg": "image/jpeg"}.get(path.suffix.lower(), "image/png")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _API_URL,
                headers={"Authorization": f"Bearer {_API_KEY}"},
                json={
                    "model": MODELS["vision"],
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
            result = resp.json()["choices"][0]["message"]["content"]
            success("vision", f"got {len(result)} chars")
            return result
    except httpx.HTTPError as e:
        error("vision", str(e))
        return None


async def hear(audio_path: str) -> str | None:
    """Convert audio to text using Whisper (async)."""
    path = Path(audio_path)
    info("audio", f"listening to {path.name}")
    try:
        from groq import Groq
        import asyncio
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        loop = asyncio.get_event_loop()
        
        def _transcribe():
            with path.open("rb") as f:
                result = client.audio.transcriptions.create(
                    file=f, model="whisper-large-v3"
                )
            return result.text
        
        result = await loop.run_in_executor(None, _transcribe)
        success("audio", f"got {len(result)} chars")
        return result
    except Exception as e:
        error("audio", str(e))
        return None