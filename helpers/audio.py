"""Helper - Audio transcription using Groq Whisper API.

Provides audio transcription functionality for quiz audio files.
"""

import tempfile
from pathlib import Path

import httpx
from groq import AsyncGroq

from config import GROQ_API_KEY


async def transcribe_url(url: str) -> str:
    """Transcribe audio from URL.

    Downloads audio file and transcribes it using Groq Whisper API.

    Args:
        url: URL to audio file (mp3, opus, wav, etc.).

    Returns:
        str: Transcribed text.

    Example:
        >>> text = await transcribe_url("https://example.com/audio.mp3")
        >>> print(text)
        Calculate the sum of all values greater than...

    Note:
        Requires GROQ_API_KEY environment variable.
    """
    # Download audio file
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60)
        content = response.content

    # Save to temp file
    suffix = Path(url).suffix or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(content)
        temp_path = f.name

    # Transcribe
    result = await transcribe_file(temp_path)

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)

    return result


async def transcribe_file(file_path: str) -> str:
    """Transcribe audio file using Groq Whisper.

    Args:
        file_path: Path to audio file on disk.

    Returns:
        str: Transcribed text.

    Raises:
        Exception: If transcription fails.
    """
    client = AsyncGroq(api_key=GROQ_API_KEY)

    with open(file_path, "rb") as audio_file:
        transcription = await client.audio.transcriptions.create(
            file=audio_file, model="whisper-large-v3-turbo", response_format="text"
        )

    return transcription
