# GreenCode — Carbon-Aware Code Review Assistant

A working prototype built for the **1M1B AI for Sustainability Virtual Internship** (in collaboration with IBM SkillsBuild & AICTE), aligned with **SDG 13: Climate Action**.

GreenCode scans Python code for energy-inefficient patterns using static analysis, scores it 0–100, and uses **IBM Granite** (via IBM watsonx.ai) to generate a plain-language explanation and fix suggestions — grounded strictly in what the analyzer actually detected.

Tested end-to-end: bad code scores 0/100 with 10 flagged issues; the same logic rewritten efficiently scores 100/100 with 0 issues, confirming the analyzer isn't just flagging everything indiscriminately.

## How it works

```
Python Code → AST Analyzer (7 pattern detectors) → Efficiency Score (0-100)
                                                          ↓
                                    IBM Granite (granite-4-h-small) → Explanation + fix
```

The analyzer's findings are the **only** input to Granite's prompt — it is explicitly instructed not to invent additional issues, keeping the generated explanation grounded in real, deterministic detections rather than free-floating generation.

## Files

| File | What it does |
|---|---|
| `analyzer.py` | Core detection engine — uses Python's `ast` module to find 7 energy-inefficient code patterns (nested loops, unmemoized recursion, `pandas.iterrows()`, etc.). |
| `carbon_score.py` | Converts detected issues into a 0–100 "Green Efficiency Score" and a Low/Medium/High relative impact estimate. |
| `message_generator.py` | Calls IBM Granite (via watsonx.ai) to turn each finding into a plain-language explanation + fix suggestion, grounded in the analyzer's real output. Falls back to a template summary if the API call fails, so a live demo never crashes. |
| `app.py` | The live Streamlit demo — paste code, get the score, browse findings, see the AI-generated summary. |
| `sample_code/inefficient_example.py` | Intentionally bad code — every anti-pattern the analyzer catches, in one file. |
| `sample_code/efficient_example.py` | Same functionality written efficiently — scores 100/100, proves the analyzer isn't just flagging everything. |
| `requirements.txt` | Python packages needed. |
| `.env.example` | Template showing the credential format needed for real Granite calls (no real secrets in this file). |

## Setup — VS Code on Windows, step by step

**1. Clone or download this repo**, then open the folder in VS Code (make sure `sample_code/` came with it as a subfolder).

**2. Open a terminal**: Terminal → New Terminal.

**3. Create and activate a virtual environment:**
```
python -m venv venv
.\venv\Scripts\Activate.ps1
```
If you get an execution-policy error:
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
then retry. You should see `(venv)` at the start of the line.

**4. Install dependencies:**
```
pip install -r requirements.txt
```

**5. (Optional) Set up real IBM Granite calls.**
Without this step, the app runs fine in template mode — it'll show a rule-based summary instead of a Granite-generated one, and clearly labels itself as doing so.

To enable real Granite generation:
1. Copy `.env.example` to a new file named exactly `.env`
2. Fill in your real IBM watsonx.ai credentials:
```
WATSONX_API_KEY=your-actual-api-key-here
WATSONX_PROJECT_ID=your-actual-project-id-here
WATSONX_URL=https://eu-de.ml.cloud.ibm.com
```
3. Open `message_generator.py` and change `USE_GRANITE = False` to `USE_GRANITE = True`
4. **Never commit your real `.env` file** — it's already excluded via `.gitignore` if you're working from a fresh clone.

**6. Run the app:**
```
streamlit run app.py
```

**7. Using the app:**
- Click **"Load inefficient sample"** → Analyze → see 10 flagged issues, score 0/100.
- Click **"Load efficient sample"** → Analyze → see 0 issues, score 100/100.
- Or paste your own Python code and see what it finds.

## IBM Bob usage

IBM Bob (in VS Code) was used for two genuine purposes during development, not added artificially to satisfy a requirement:
- **Ideation**: reviewed `analyzer.py` and helped identify which additional inefficiency patterns were worth detecting, prioritized by likely energy impact.
- **Debugging**: a full code review from Bob caught 4 real bugs — a scoring bug where triple-nested loops were over-penalized, a UI bug duplicating line-number text in finding cards, a silent no-op when clicking Analyze with empty input, and an unsafe file read with no encoding/error handling. All 4 were fixed and verified.

## Responsible AI

- **Transparency**: every score is explained line-by-line with the exact pattern matched — never a black-box number.
- **Honesty about limitations**: the score is explicitly labeled a relative, educational estimate based on known algorithmic anti-patterns — not a measured energy/CO2 figure. Real measurement would require hardware-level profiling (e.g. CodeCarbon).
- **No hallucinated findings**: Granite is only shown the analyzer's actual detected issues and explicitly instructed not to invent additional ones.
- **No data collection**: code pasted into the app stays in-session only; nothing is stored or transmitted beyond the single Granite API call.
- **Graceful failure**: if the Granite API call fails, the app falls back to a template summary instead of crashing mid-demo.

## Known limitations & future scope

- Covers 7 patterns; many other inefficiencies exist undetected.
- Async recursive functions (`async def` calling itself) aren't yet detected — a known gap.
- No real hardware-level energy profiling — the score is a relative estimate, not a measured figure.
- Future scope: broader pattern coverage, real profiling integration, multi-language support (JS/Java), and a VS Code extension for real-time inline feedback while typing.