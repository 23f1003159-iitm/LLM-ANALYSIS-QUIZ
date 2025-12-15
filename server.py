"""FastAPI Server for Quiz Solving API.

This is the main API endpoint that receives POST requests with quiz URLs
and solves them automatically using the LLM-based quiz solver.
"""

import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import solve_quiz
from config import SECRET_KEY
from logs.logger import get_logger

logger = get_logger("server")

# Quiz timeout in seconds (3 minutes)
QUIZ_TIMEOUT = 180


class QuizRequest(BaseModel):
    """Incoming quiz request payload."""

    email: str
    secret: str
    url: str


class QuizResponse(BaseModel):
    """Response after solving a quiz."""

    correct: bool
    url: str | None = None
    reason: str | None = None
    solved_count: int = 0


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler."""
    logger.info("🚀 Quiz Solver API starting...")
    yield
    logger.info("👋 Quiz Solver API shutting down...")


app = FastAPI(
    title="Quiz Solver API",
    description="Autonomous quiz solving API using LLMs",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "quiz-solver"}


@app.post("/quiz", response_model=QuizResponse)
async def solve_quiz_endpoint(request: QuizRequest):
    """Main quiz solving endpoint."""
    # Verify secret
    if request.secret != SECRET_KEY:
        logger.warning(f"Invalid secret from {request.email}")
        raise HTTPException(status_code=403, detail="Invalid secret")

    logger.info(f"📝 Quiz request from {request.email}: {request.url}")

    start_time = time.time()
    current_url = request.url
    solved_count = 0
    last_result = None

    try:
        while current_url:
            elapsed = time.time() - start_time
            if elapsed > QUIZ_TIMEOUT:
                logger.warning(f"⏰ Timeout after {elapsed:.1f}s")
                break

            logger.info(f"🔄 Solving quiz {solved_count + 1}: {current_url}")

            try:
                result = await asyncio.wait_for(
                    solve_quiz(current_url), timeout=QUIZ_TIMEOUT - elapsed
                )
            except TimeoutError:
                logger.error("⏰ Single quiz timeout")
                break

            last_result = result
            elapsed = time.time() - start_time
            time_left = max(0, QUIZ_TIMEOUT - elapsed)

            if result.get("correct"):
                solved_count += 1
                logger.info(f"✅ Q{solved_count} Correct! ⏱️ {time_left:.0f}s left")
                current_url = result.get("next_url")
            else:
                logger.warning(f"❌ Wrong: {result.get('reason', 'Unknown')}")
                next_url = result.get("next_url")
                if next_url:
                    logger.info(f"⏭️ Skipping to next: {next_url}")
                    current_url = next_url
                else:
                    break

        elapsed = time.time() - start_time
        logger.info(f"📊 Done: {solved_count} solved in {elapsed:.1f}s")

        return QuizResponse(
            correct=last_result.get("correct", False) if last_result else False,
            url=last_result.get("next_url") if last_result else None,
            reason=last_result.get("reason") if last_result else None,
            solved_count=solved_count,
        )

    except Exception as e:
        logger.error(f"💥 Error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
