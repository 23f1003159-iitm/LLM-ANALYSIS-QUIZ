"""Core Submitter - Submit answer to quiz endpoint.

This module handles submitting answers to the quiz API and parsing responses.
"""

from urllib.parse import urljoin

from helpers import post_json
from logs.logger import get_logger

logger = get_logger("submitter")


async def submit(url: str, email: str, secret: str, quiz_url: str, answer: str) -> dict:
    """Submit answer to quiz endpoint.

    Sends the answer along with credentials to the quiz submission endpoint
    and returns the result including whether it was correct and next URL.

    Args:
        url: Submit endpoint URL (can be relative).
        email: User email for authentication.
        secret: Secret key for authentication.
        quiz_url: Original quiz URL (for resolving relative submit URLs).
        answer: The answer to submit.

    Returns:
        dict: Submission result containing:
            - success (bool): Whether submission succeeded
            - correct (bool): Whether answer was correct
            - reason (str): Error message if wrong
            - next_url (str): URL to next quiz if available

    Example:
        >>> result = await submit(
        ...     url="/submit",
        ...     email="user@example.com",
        ...     secret="key123",
        ...     quiz_url="https://quiz.com/q1",
        ...     answer="42"
        ... )
        >>> print(result['correct'])
        True
    """
    # Resolve submit URL (handle relative URLs)
    if not url.startswith("http"):
        url = urljoin(quiz_url, url)

    logger.debug(f"Submitting to: {url}")

    payload = {
        "email": email,
        "secret": secret,
        "url": quiz_url,
        "answer": answer,
    }

    try:
        response = await post_json(url, payload)
        logger.debug(f"Submit response: {response}")

        return {
            "success": True,
            "correct": response.get("correct", False),
            "reason": response.get("reason", ""),
            "next_url": response.get("url"),
        }

    except Exception as e:
        logger.error(f"Submission failed: {e}")
        return {
            "success": False,
            "correct": False,
            "reason": str(e),
            "next_url": None,
        }
