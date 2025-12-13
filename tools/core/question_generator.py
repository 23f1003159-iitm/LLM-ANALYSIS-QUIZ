"""Generate questions from all downloaded quiz data."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import error, info, success
from llm import call
from tools.helper.paths import get_session_dir, list_input_files, get_question_path
from tools.helper.data_reader import read_csv, read_file


async def generate(quiz_url: str, page_text: str = "") -> dict:
    """
    Read all data from session folder and generate the question.
    
    Args:
        quiz_url: the quiz url (used to find session folder)
        page_text: text from the webpage
    
    Returns:
        dict with question, context, answer_type, submit_url
    """
    info("question", "gathering all data")
    
    session_dir = get_session_dir(quiz_url)
    info("question", f"📁 SESSION: {session_dir.name}")
    
    # Get only INPUT files (excludes generated outputs)
    input_files = list_input_files(quiz_url)
    info("question", f"📥 {len(input_files)} input files")
    
    context_parts = []
    
    if page_text:
        context_parts.append(f"PAGE TEXT:\n{page_text}")
    
    for f in input_files:
        ext = f.suffix.lower()
        info("question", f"  📄 processing: {f.name}")
        
        if "_transcript.txt" in f.name:
            text = f.read_text()
            context_parts.append(f"AUDIO TRANSCRIPT:\n{text}")
        
        elif "_vision.txt" in f.name:
            text = f.read_text()
            context_parts.append(f"IMAGE CONTENT:\n{text}")
        
        elif ext == ".csv":
            result = await read_csv(str(f))
            if result["success"]:
                context_parts.append(f"CSV DATA:\n{result['text'][:2000]}")
        
        elif ext == ".json":
            text = f.read_text()
            context_parts.append(f"JSON DATA:\n{text[:1000]}")
    
    full_context = "\n\n".join(context_parts)
    
    info("question", f"collected {len(context_parts)} data sources")
    
    # Step 1: Analyze available data and create custom extraction strategy
    data_types = []
    if any("PAGE TEXT" in part for part in context_parts):
        data_types.append("web page text")
    if any("AUDIO TRANSCRIPT" in part for part in context_parts):
        data_types.append("audio transcript")
    if any("IMAGE CONTENT" in part for part in context_parts):
        data_types.append("screenshot/image analysis")
    if any("CSV DATA" in part for part in context_parts):
        data_types.append("CSV data file")
    if any("JSON DATA" in part for part in context_parts):
        data_types.append("JSON data file")
    
    data_summary = ", ".join(data_types) if data_types else "unknown sources"
    
    # Step 2: LLM creates a custom extraction strategy for THIS specific quiz
    strategy_prompt = f"""You are analyzing a quiz. Available data: {data_summary}

Preview of data:
{full_context[:1000]}...

YOUR TASK: Create a PERFECT extraction strategy for this specific quiz.

Analyze:
1. Where is the question stated? (audio, page text, image?)
2. What key numbers/values are mentioned? (cutoffs, IDs, thresholds?)
3. What's the answer format? (number, text, boolean, json?)
4. Where's the submit URL?

Write extraction instructions (be specific to THIS quiz, not generic):"""
    
    strategy = await call(strategy_prompt, task="fast")
    
    # Step 3: Use the custom strategy to extract the question
    extraction_prompt = f"""Using this strategy:
{strategy}

Extract from this data:
{full_context}

Output in EXACT format:
QUESTION: [exact question]
CONTEXT: [key values, filenames, column names]
ANSWER_TYPE: [number/text/boolean/json]
SUBMIT_URL: [exact URL]
INSTRUCTIONS: [formatting requirements]"""
    
    response = await call(extraction_prompt, task="reason")
    if not response:
        error("question", "llm failed")
        return {"success": False, "error": "llm failed"}
    
    result = _parse_response(response)
    result["success"] = True
    result["session_dir"] = str(session_dir)
    
    # Save question to JSON file
    question_file = session_dir / "question.json"
    question_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    info("question", f"saved to {question_file.name}")
    
    success("question", f"question: {result.get('question', '')[:50]}...")
    return result


def _parse_response(response: str) -> dict:
    """Extract structured data from LLM response."""
    import re
    
    result = {
        "question": "",
        "context": "",
        "answer_type": "text",
        "submit_url": "",
        "instructions": "",
    }
    
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("QUESTION:"):
            result["question"] = _clean_value(line.replace("QUESTION:", ""))
        elif line.startswith("CONTEXT:"):
            result["context"] = _clean_value(line.replace("CONTEXT:", ""))
        elif line.startswith("ANSWER_TYPE:"):
            result["answer_type"] = _clean_value(line.replace("ANSWER_TYPE:", "")).lower()
        elif line.startswith("SUBMIT_URL:"):
            url = _clean_value(line.replace("SUBMIT_URL:", ""))
            # Extract URL from brackets or markdown links
            url_match = re.search(r'https?://[^\s\[\]<>"\'\)]+', url)
            if url_match:
                url = url_match.group(0)
            result["submit_url"] = url
        elif line.startswith("INSTRUCTIONS:"):
            result["instructions"] = _clean_value(line.replace("INSTRUCTIONS:", ""))
    
    return result


def _clean_value(value: str) -> str:
    """Clean LLM output - remove brackets, backticks, quotes."""
    value = value.strip()
    # Remove markdown code blocks
    value = value.replace("```", "")
    # Remove brackets
    value = value.strip("[]")
    # Remove quotes
    value = value.strip("\"'")
    return value.strip()

