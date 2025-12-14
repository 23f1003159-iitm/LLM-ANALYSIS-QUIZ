"""Helper - ZIP archive operations.

Provides utilities for creating, extracting, and listing ZIP archives.
"""

import tempfile
import zipfile
from io import BytesIO
from pathlib import Path


def unzip(zip_path: str, extract_dir: str = None) -> list:
    """Unzip file and return list of extracted files.

    Args:
        zip_path: Path to ZIP file.
        extract_dir: Directory to extract to (creates temp dir if None).

    Returns:
        list: Absolute paths to extracted files.

    Example:
        >>> files = unzip("archive.zip")
        >>> print(files)
        ['/tmp/tmpxyz/file1.txt', '/tmp/tmpxyz/file2.csv']
    """
    if extract_dir is None:
        extract_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
        files = zf.namelist()

    return [str(Path(extract_dir) / f) for f in files]


def unzip_bytes(zip_bytes: bytes, extract_dir: str = None) -> list:
    """Unzip from bytes and return list of extracted files.

    Args:
        zip_bytes: ZIP file content as bytes.
        extract_dir: Directory to extract to (creates temp dir if None).

    Returns:
        list: Absolute paths to extracted files.
    """
    if extract_dir is None:
        extract_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
        zf.extractall(extract_dir)
        files = zf.namelist()

    return [str(Path(extract_dir) / f) for f in files]


def create_zip(files: list, output_path: str) -> str:
    """Create zip from list of file paths.

    Args:
        files: List of file paths to include.
        output_path: Path for output ZIP file.

    Returns:
        str: Path to created ZIP file.

    Example:
        >>> create_zip(["file1.txt", "file2.csv"], "archive.zip")
        'archive.zip'
    """
    with zipfile.ZipFile(output_path, "w") as zf:
        for f in files:
            zf.write(f, Path(f).name)
    return output_path


def list_zip(zip_path: str) -> list:
    """List contents of zip file.

    Args:
        zip_path: Path to ZIP file.

    Returns:
        list: List of filenames in the archive.

    Example:
        >>> contents = list_zip("archive.zip")
        >>> print(contents)
        ['file1.txt', 'file2.csv', 'data/file3.json']
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        return zf.namelist()
