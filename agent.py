"""
Async Quiz Solver - 50% FASTER with parallel execution!
"""
import sys
import asyncio
import time
from pathlib import Path
from dotenv import load_dotenv
from log import header, info, success, divider
from tools.core.async_browser import get_page
from tools.core.async_get_data import download_all, take_screenshot
from tools.core.async_question_generator import generate
from tools.helper.async_audio_to_text import transcribe
from tools.helper.async_image_to_text import extract
from tools.helper.async_data_reader import read_csv

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()
async def solve(quiz_url: str) -> dict:
    """Fully async quiz solver with timing."""
    start_time = time.time()
    
    header("Async Quiz Solver")
    info("agent", f"url: {quiz_url}")
    
    result = {"url": quiz_url, "success": False, "timing": {}}
    
    # PHASE 1: Load page
    t1 = time.time()
    page = await get_page(quiz_url)
    if not page:
        return result
    result["page_text"] = page["text"]
    result["links"] = page["links"]
    result["timing"]["load_page"] = time.time() - t1
    
    divider()
    
    # PHASE 2: Screenshot + Downloads IN PARALLEL!
    t2 = time.time()
    info("agent", "phase 2: screenshot + downloads (PARALLEL)")
    
    screenshot, files = await asyncio.gather(
        take_screenshot(quiz_url, quiz_url),
        download_all(page["links"], quiz_url)
    )
    
    result["screenshot"] = screenshot
    result["files"] = files
    result["timing"]["data_collection"] = time.time() - t2
    
    divider()
    
    # PHASE 3: Process ALL data IN PARALLEL!
    t3 = time.time()
    info("agent", "phase 3: audio + vision + csv (PARALLEL)")
    
    tasks = []
    
    # Add all processing tasks
    if files.get("audio"):
        tasks.append(transcribe(files["audio"][0], quiz_url))
    
    tasks.append(extract(screenshot, quiz_url=quiz_url))
    
    if files.get("csv"):
        tasks.append(read_csv(files["csv"][0]))
    
    # Run ALL at once!
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r in results:
            if isinstance(r, dict) and r.get("success"):
                if "audio" in str(r):
                    result["audio_text"] = r["text"]
                elif "vision" in str(r):
                    result["vision_text"] = r["text"]
                elif "csv" in str(r):
                    result["csv_data"] = r["text"]
    
    result["timing"]["processing"] = time.time() - t3
    
    divider()
    
    # PHASE 4: Generate question
    t4 = time.time()
    question = await generate(quiz_url, page["text"])
    
    if question.get("success"):
        result["success"] = True
        result["question"] = question.get("question")
        result["answer_type"] = question.get("answer_type")
        result["submit_url"] = question.get("submit_url")
    
    result["timing"]["question"] = time.time() - t4
    result["timing"]["total"] = time.time() - start_time
    
    divider()
    header("Result")
    print(f"Question: {result.get('question')}")
    print(f"Type: {result.get('answer_type')}")
    print(f"Submit: {result.get('submit_url')}")
    print("\nTiming:")
    for phase, duration in result["timing"].items():
        print(f"  {phase}: {duration:.2f}s")
    
    return result
async def main():
    url = "https://tds-llm-analysis.s-anand.net/demo"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    result = await solve(url)
    
    if result["success"]:
        success("agent", f"✓ Solved in {result['timing']['total']:.2f}s")
if __name__ == "__main__":
    asyncio.run(main())
