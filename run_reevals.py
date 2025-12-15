"""Run Project 2 Re-evaluations."""

import asyncio

from agent import solve_quiz
from logs.logger import get_logger

logger = get_logger("reevals")


async def run_reevals():
    """Run all 24 re-evaluation questions."""
    start_url = "https://tds-llm-analysis.s-anand.net/project2-reevals"
    urls = [start_url]
    results = []

    print("\n" + "=" * 50)
    print("🎯 Project 2 Re-evaluations")
    print("=" * 50 + "\n")

    for i, url in enumerate(urls):
        print(f"\n📝 Question {i + 1}")
        print(f"   URL: {url}")

        try:
            result = await solve_quiz(url)
            correct = result.get("correct", False)
            results.append(correct)

            if correct:
                print("   ✅ CORRECT")
            else:
                reason = result.get("reason", "Unknown")
                print(f"   ❌ WRONG: {reason}")

            next_url = result.get("next_url")
            if next_url:
                urls.append(next_url)
                print(f"   ➡️  Next: {next_url}")
            else:
                print("   🏁 No more questions")

        except Exception as e:
            logger.error(f"Error on question {i + 1}: {e}")
            print(f"   ⚠️ ERROR: {e}")
            results.append(False)

    correct_count = sum(results)
    total_count = len(results)
    percentage = (correct_count / total_count * 100) if total_count > 0 else 0

    print("\n" + "=" * 50)
    print("📊 Final Results")
    print("=" * 50)
    print(f"   Correct: {correct_count}/{total_count} ({percentage:.1f}%)")
    print("=" * 50 + "\n")

    return results


if __name__ == "__main__":
    asyncio.run(run_reevals())
