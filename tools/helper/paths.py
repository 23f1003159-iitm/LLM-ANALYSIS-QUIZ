"""Centralized path management for quiz sessions."""
import hashlib
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Base data folder
DATA_DIR = PROJECT_ROOT / "data"
SESSIONS_DIR = DATA_DIR / "sessions"


def get_session_dir(quiz_url: str) -> Path:
    """
    Get unique folder for each quiz session.
    Uses URL hash so each quiz gets its own folder.
    """
    url_hash = hashlib.md5(quiz_url.encode()).hexdigest()[:8]
    session_dir = SESSIONS_DIR / url_hash
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def get_file_path(quiz_url: str, filename: str) -> Path:
    """Get path for a file in the session folder."""
    return get_session_dir(quiz_url) / filename


# ===== INPUT FILES =====
def get_screenshot_path(quiz_url: str) -> Path:
    """Get path for quiz screenshot."""
    return get_file_path(quiz_url, "screenshot.png")


def get_audio_path(quiz_url: str, filename: str) -> Path:
    """Get path for audio file."""
    return get_file_path(quiz_url, filename)


def get_csv_path(quiz_url: str, filename: str) -> Path:
    """Get path for CSV file."""
    return get_file_path(quiz_url, filename)


def get_pdf_path(quiz_url: str, filename: str) -> Path:
    """Get path for PDF file."""
    return get_file_path(quiz_url, filename)


# ===== OUTPUT FILES =====
def get_question_path(quiz_url: str) -> Path:
    """Get path for question.json."""
    return get_file_path(quiz_url, "question.json")


def get_answer_path(quiz_url: str) -> Path:
    """Get path for answer.json."""
    return get_file_path(quiz_url, "answer.json")


def get_prompt_path(quiz_url: str) -> Path:
    """Get path for instruction_prompt.txt."""
    return get_file_path(quiz_url, "instruction_prompt.txt")


def get_code_path(quiz_url: str) -> Path:
    """Get path for generated_code.py."""
    return get_file_path(quiz_url, "generated_code.py")


def get_chart_path(quiz_url: str, name: str = "chart.png") -> Path:
    """Get path for generated chart."""
    return get_file_path(quiz_url, name)


# ===== FILE LISTING =====
def list_session_files(quiz_url: str) -> list[Path]:
    """List all files in quiz session folder."""
    session_dir = get_session_dir(quiz_url)
    return list(session_dir.glob("*"))


def list_input_files(quiz_url: str) -> list[Path]:
    """List only INPUT files (not generated outputs)."""
    output_files = {
        "question.json",
        "answer.json",
        "code.json",
        "generated_code.py",
        "solve_metadata.json",
        "instruction_prompt.txt",
    }
    all_files = list_session_files(quiz_url)
    return [f for f in all_files if f.name not in output_files and f.is_file()]


def list_files_by_type(quiz_url: str) -> dict:
    """List files categorized by type."""
    files = list_input_files(quiz_url)
    
    categorized = {
        "audio": [],
        "csv": [],
        "pdf": [],
        "json": [],
        "excel": [],
        "image": [],
        "text": [],
        "other": [],
    }
    
    for f in files:
        ext = f.suffix.lower()
        if ext in (".mp3", ".wav", ".opus", ".m4a", ".ogg"):
            categorized["audio"].append(f)
        elif ext == ".csv":
            categorized["csv"].append(f)
        elif ext == ".pdf":
            categorized["pdf"].append(f)
        elif ext == ".json":
            categorized["json"].append(f)
        elif ext in (".xlsx", ".xls"):
            categorized["excel"].append(f)
        elif ext in (".png", ".jpg", ".jpeg", ".gif"):
            categorized["image"].append(f)
        elif ext in (".txt", ".md", ".html"):
            categorized["text"].append(f)
        else:
            categorized["other"].append(f)
    
    return {k: v for k, v in categorized.items() if v}


# ===== CLEANUP =====
def clean_session(quiz_url: str) -> None:
    """Delete all files in quiz session folder."""
    session_dir = get_session_dir(quiz_url)
    for f in session_dir.glob("*"):
        if f.is_file():
            f.unlink()


def clean_outputs(quiz_url: str) -> None:
    """Delete only generated output files (keep inputs)."""
    output_files = {
        "question.json",
        "answer.json",
        "code.json", 
        "generated_code.py",
        "solve_metadata.json",
        "instruction_prompt.txt",
    }
    session_dir = get_session_dir(quiz_url)
    for f in session_dir.glob("*"):
        if f.name in output_files:
            f.unlink()


if __name__ == "__main__":
    # Test
    url = "https://example.com/quiz-test"
    
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Session dir: {get_session_dir(url)}")
    print(f"Screenshot: {get_screenshot_path(url)}")
    print(f"Question: {get_question_path(url)}")
    print(f"Answer: {get_answer_path(url)}")