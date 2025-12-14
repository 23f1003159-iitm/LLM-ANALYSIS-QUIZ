"""Helper - File operations (download and read).

Provides utilities for downloading files from URLs and reading their contents.
"""

import tempfile
from pathlib import Path

import httpx


async def download(url: str) -> str:
    """Download file from URL to temp location.

    Args:
        url: URL to download from.

    Returns:
        str: Path to downloaded file.

    Example:
        >>> path = await download("https://example.com/data.csv")
        >>> print(path)
        /tmp/tmpxyz123.csv
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60)
        content = response.content

    # Preserve file extension
    suffix = Path(url).suffix or ".tmp"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(content)
        return f.name


def read_text(path: str) -> str:
    """Read text file content.

    Args:
        path: Path to file.

    Returns:
        str: File contents as text.

    Raises:
        UnicodeDecodeError: If file is not valid text.
    """
    return Path(path).read_text()


def read_bytes(path: str) -> bytes:
    """Read file as bytes.

    Args:
        path: Path to file.

    Returns:
        bytes: File contents as bytes.
    """
    return Path(path).read_bytes()
