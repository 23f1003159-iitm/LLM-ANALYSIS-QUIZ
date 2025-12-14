"""Helper - HTML/CSV/JSON parsing and parameter extraction.

Provides parsing utilities for various data formats commonly found in quizzes.
"""

import json
import re
from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup


def parse_html(html: str) -> dict:
    """Parse HTML to extract media and links.

    Args:
        html: HTML string to parse.

    Returns:
        dict: Parsed data containing:
            - audio (list): Audio source URLs
            - files (list): File link dicts with href and text
            - links (list): All link dicts with href and text

    Example:
        >>> html = '<audio src="demo.mp3"></audio><a href="data.csv">CSV</a>'
        >>> result = parse_html(html)
        >>> print(result['audio'])
        ['demo.mp3']
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract audio sources
    audio = [tag.get("src") for tag in soup.find_all("audio") if tag.get("src")]

    # Extract file links (a tags with href to files)
    files = []
    for tag in soup.find_all("a", href=True):
        href = tag.get("href")
        # Consider it a file if it has an extension
        if "." in href.split("/")[-1]:
            files.append({"href": href, "text": tag.get_text(strip=True)})

    # Extract all links
    links = [
        {"href": tag.get("href"), "text": tag.get_text(strip=True)}
        for tag in soup.find_all("a", href=True)
    ]

    return {"audio": audio, "files": files, "links": links}


def parse_csv(csv_text: str) -> pd.DataFrame:
    """Parse CSV text to DataFrame.

    Args:
        csv_text: CSV content as string.

    Returns:
        pd.DataFrame: Parsed DataFrame with no headers.

    Example:
        >>> csv = "0\\n12345\\n67890"
        >>> df = parse_csv(csv)
        >>> print(df[0].sum())
        80235
    """
    return pd.read_csv(StringIO(csv_text), header=None)


def parse_json(json_text: str) -> dict | list:
    """Parse JSON text to Python object.

    Args:
        json_text: JSON content as string.

    Returns:
        dict | list: Parsed JSON object.

    Raises:
        json.JSONDecodeError: If JSON is invalid.
    """
    return json.loads(json_text)


def extract_params(text: str) -> dict:
    """Extract parameters from text.

    Looks for common patterns like:
    - "Cutoff: 12345" or "cutoff=12345"
    - Email addresses

    Args:
        text: Text to extract from.

    Returns:
        dict: Extracted parameters (cutoff, email, etc.).

    Example:
        >>> text = "Calculate sum with cutoff: 64239. Email: user@example.com"
        >>> params = extract_params(text)
        >>> print(params)
        {'cutoff': 64239, 'email': 'user@example.com'}
    """
    params = {}

    # Extract cutoff value
    cutoff_match = re.search(r"cutoff[:\s=]+(\d+)", text, re.IGNORECASE)
    if cutoff_match:
        params["cutoff"] = int(cutoff_match.group(1))

    # Extract email
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    if email_match:
        params["email"] = email_match.group(0)

    return params
