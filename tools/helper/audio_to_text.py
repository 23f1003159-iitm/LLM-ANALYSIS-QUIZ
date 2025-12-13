"""Convert audio files to text using Whisper."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import error, info, success
from tools.helper.paths import get_session_dir

load_dotenv()


async def transcribe(audio_path: str, quiz_url: str | None = None) -> dict:
    """Turn audio to text. Save transcript if quiz_url provided."""
    path = Path(audio_path)
    if not path.exists():
        error("audio", f"file not found: {path}")
        return {"success": False, "text": "", "error": "file not found"}
    
    info("audio", f"transcribing {path.name}")
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        loop = asyncio.get_event_loop()
        
        def _transcribe():
            with path.open("rb") as f:
                result = client.audio.transcriptions.create(file=f, model="whisper-large-v3")
            return result.text
        
        text = await loop.run_in_executor(None, _transcribe)
        
        if quiz_url:
            session_dir = get_session_dir(quiz_url)
            transcript_file = session_dir / f"{path.stem}_transcript.txt"
            transcript_file.write_text(text)
            info("audio", f"saved transcript to {transcript_file.name}")
        
        success("audio", f"got {len(text)} chars")
        return {"success": True, "text": text, "error": ""}
    except Exception as e:
        error("audio", str(e))
        return {"success": False, "text": "", "error": str(e)}
