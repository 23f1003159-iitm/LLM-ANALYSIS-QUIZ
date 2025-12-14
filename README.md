# LLM Quiz Solver 🎯

*An AI agent that actually solves quizzes on its own - and gets them all right.*

## What is this?

Ever wondered if an AI could actually solve complex, multi-step problems without human intervention? This project answers that question with a resounding yes.

I built an autonomous agent powered by Meta's Llama 3.3 70B that tackles dynamic quiz questions. It doesn't just answer simple questions - it scrapes web pages, transcribes audio, processes data, writes Python code, and submits answers. All by itself.

**The result?** 100% success rate.

## The Challenge

The quizzes aren't straightforward. They throw curveballs:
- Audio files you need to transcribe and analyze
- CSV datasets requiring filtering and calculations  
- SQL databases to query
- Base64-encoded secrets to decode
- ZIP archives to extract and process
- YAML configurations to format

Each question is different. The agent can't rely on patterns - it has to think, decide which tools to use, and execute a plan.

## How It Works

Think of it as an AI that controls other tools, like a conductor leading an orchestra.

**The Flow:**
1. **Scrapes** the quiz page (text, audio, files, parameters)
2. **Converts** everything into a format the LLM understands
3. **Thinks** - the LLM decides what to do next
4. **Acts** - runs Python code, scrapes more pages, or submits the answer
5. **Repeats** until the quiz is solved

It's not pre-programmed. Give it a new type of question it hasn't seen, and it figures it out.

## Why This Matters

This isn't just another AI demo. It's a practical example of:
- **Tool orchestration** - An LLM deciding which tools to use and when
- **Autonomous problem solving** - No human in the loop
- **Real-world complexity** - Handling audio, databases, encoding, multiple data formats
- **Production-quality code** - Clean architecture, professional logging, comprehensive docs

## Quick Start

**Prerequisites:**
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (fast Python package manager)
- API keys for NVIDIA NIM and Groq

**Get Running:**

```bash
# Clone and setup
git clone https://github.com/23f1003159-iitm/LLM-ANALYSIS-QUIZ.git
cd LLM-ANALYSIS-QUIZ
uv sync
uv run playwright install chromium

# Configure (add your API keys)
cp .env.example .env
# Edit .env with your keys

# Run it
uv run python -c "
import asyncio
from agent import solve_quiz

async def test():
    result = await solve_quiz('https://tds-llm-analysis.s-anand.net/demo')
    print(f'Result: {\"✓ Correct\" if result[\"correct\"] else \"✗ Wrong\"}')

asyncio.run(test())
"
```

## Project Structure

The code is deliberately simple and modular:

```
├── agent.py           # The brain - LLM orchestrator
├── core/              # Core capabilities
│   ├── scraper.py     # Web scraping
│   ├── converter.py   # Data processing
│   ├── runner.py      # Code execution
│   └── submitter.py   # Answer submission
├── helpers/           # Utilities
│   ├── web.py         # HTTP & browser
│   ├── audio.py       # Transcription
│   ├── file.py        # File operations
│   ├── parser.py      # Parsing
│   ├── code.py        # Sandboxed execution
│   ├── sql.py         # Database queries
│   ├── bs64_encoding.py # Base64
│   └── unzip_zip.py   # ZIP handling
└── llm/               # LLM interface
    ├── client.py      # API client
    └── prompts.py     # System prompt
```

Each file does one thing well. No magic, no unnecessary complexity.

## The Tech

- **LLM**: Meta Llama 3.3 70B Instruct (via NVIDIA NIM)
- **Audio**: Groq Whisper API for transcription
- **Web**: Playwright for headless browsing
- **Data**: pandas, numpy, sqlite3
- **Quality**: ruff for linting and formatting

## What I Learned

Building this taught me that LLM agents are most effective when:
1. **Tools are simple** - Each tool does one thing clearly
2. **Context is key** - The LLM needs all the data, formatted right
3. **Prompts matter** - Spent as much time on the prompt as the code
4. **Logging saves time** - Session-based logs with colors made debugging actually pleasant
5. **Iteration is crucial** - Went from 81% to 100% by refining the prompt

## The Results

| Metric | Result |
|--------|--------|
| **Success Rate** | 100% |
| **Avg Time/Question** | ~8 seconds |
| **Questions Types Handled** | CSV, Audio, SQL, Base64, ZIP, JSON, YAML, Shell |

## Running the Full Test

```bash
uv run python -c "
import asyncio
from agent import solve_quiz

async def test():
    urls = ['https://tds-llm-analysis.s-anand.net/demo']
    results = []
    
    for i, url in enumerate(urls):
        result = await solve_quiz(url)
        results.append(result.get('correct', False))
        print(f'Q{i+1}: {\"✓\" if result.get(\"correct\") else \"✗\"}')
        
        if result.get('next_url'):
            urls.append(result['next_url'])
    
    print(f'\nFinal: {sum(results)}/{len(results)}')

asyncio.run(test())
"
```

## Code Quality

Zero compromise on quality:
- ✅ Google-style docstrings on every function
- ✅ Zero linting errors (ruff)
- ✅ Professional logging system
- ✅ Clean, modular architecture

```bash
uv run ruff check .   # Pass
uv run ruff format .  # Pass
```

## Logging

Watch it think in real-time with color-coded logs:

- 🔵 **DEBUG** - Detailed execution (file only)
- 🟢 **INFO** - What it's doing (console + file)
- 🟡 **WARNING** - Issues it encountered
- 🔴 **ERROR** - What broke (and how it recovered)

Logs are session-based in `logs/app.log` with full execution traces.

## Environment Setup

Create a `.env` file:

```bash
NVIDIA_API_KEY=your_nvidia_key
GROQ_API_KEY=your_groq_key
EMAIL=your_email@example.com
SECRET_KEY=your_secret
```

## Contributing

If you want to improve this:
1. Keep it simple - don't over-engineer
2. Follow the existing patterns
3. Document your changes
4. Run `uv run ruff check .` before committing

## What's Next?

This is a proof of concept. Potential directions:
- Support for more data formats
- Multi-model orchestration
- Parallel tool execution
- Self-improvement via feedback loops

## License

MIT - Use it however you want.

## Links

- **GitHub**: [@23f1003159-iitm](https://github.com/23f1003159-iitm)
- **Repository**: [LLM-ANALYSIS-QUIZ](https://github.com/23f1003159-iitm/LLM-ANALYSIS-QUIZ)

## Acknowledgments

Built for the Tools in Data Science course at IIT Madras. Thanks to:
- **NVIDIA** for NIM API access
- **Groq** for Whisper API
- **Meta AI** for Llama 3.3 70B

---

*Built with curiosity and Python. Powered by Llama 3.3 70B.*
