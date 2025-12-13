"""Helper tools for quiz processing."""
from tools.helper.audio_to_text import transcribe
from tools.helper.image_to_text import extract as extract_image
from tools.helper.data_reader import read_csv, read_json, read_file, read_excel
from tools.helper.pdf_reader import read_pdf, read_pdf_tables
from tools.helper.api_caller import call_api, submit_answer
from tools.helper.scraper import scrape_url, scrape_all
from tools.helper.chart_generator import generate_chart, generate_chart_from_code
from tools.helper.code_generator import generate_code
from tools.helper.code_executor import execute_code, save_code
from tools.helper.paths import (
    PROJECT_ROOT,
    DATA_DIR,
    SESSIONS_DIR,
    get_session_dir,
    get_file_path,
    get_screenshot_path,
    get_audio_path,
    get_csv_path,
    get_pdf_path,
    get_question_path,
    get_answer_path,
    get_prompt_path,
    get_code_path,
    get_chart_path,
    list_session_files,
    list_input_files,
    list_files_by_type,
    clean_session,
    clean_outputs,
)

__all__ = [
    # Audio
    "transcribe",
    # Vision
    "extract_image",
    # Data reading
    "read_csv",
    "read_json",
    "read_file",
    "read_excel",
    "read_pdf",
    "read_pdf_tables",
    # API
    "call_api",
    "submit_answer",
    # Scraping
    "scrape_url",
    "scrape_all",
    # Charts
    "generate_chart",
    "generate_chart_from_code",
    # Code
    "generate_code",
    "execute_code",
    "save_code",
    # Paths
    "PROJECT_ROOT",
    "DATA_DIR",
    "SESSIONS_DIR",
    "get_session_dir",
    "get_file_path",
    "get_screenshot_path",
    "get_audio_path",
    "get_csv_path",
    "get_pdf_path",
    "get_question_path",
    "get_answer_path",
    "get_prompt_path",
    "get_code_path",
    "get_chart_path",
    "list_session_files",
    "list_input_files",
    "list_files_by_type",
    "clean_session",
    "clean_outputs",
]
