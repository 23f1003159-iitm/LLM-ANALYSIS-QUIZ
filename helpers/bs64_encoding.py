"""Helper - Base64 encoding and decoding.

Provides utilities for base64 encoding and decoding of strings and bytes.
"""

import base64


def encode_base64(data: str | bytes) -> str:
    """Encode string or bytes to base64.

    Args:
        data: String or bytes to encode.

    Returns:
        str: Base64 encoded string.

    Example:
        >>> encoded = encode_base64("Hello World")
        >>> print(encoded)
        SGVsbG8gV29ybGQ=
    """
    if isinstance(data, str):
        data = data.encode()
    return base64.b64encode(data).decode()


def decode_base64(data: str) -> str:
    """Decode base64 string to text.

    Args:
        data: Base64 encoded string.

    Returns:
        str: Decoded text.

    Raises:
        binascii.Error: If input is not valid base64.

    Example:
        >>> decoded = decode_base64("SGVsbG8gV29ybGQ=")
        >>> print(decoded)
        Hello World
    """
    return base64.b64decode(data).decode()


def decode_base64_bytes(data: str) -> bytes:
    """Decode base64 string to bytes.

    Args:
        data: Base64 encoded string.

    Returns:
        bytes: Decoded bytes.

    Raises:
        binascii.Error: If input is not valid base64.
    """
    return base64.b64decode(data)
