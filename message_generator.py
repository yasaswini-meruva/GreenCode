"""
message_generator.py
---------------------
Turns raw detected issues + score into a plain-language report a developer
can act on. TEMPLATE MODE works with no API key. GRANITE MODE calls the
real IBM watsonx.ai Granite model.

This is the generative layer: the analyzer (deterministic) finds WHAT is
wrong; Granite's job is to explain WHY it matters and suggest a fix in
clear language -- that's the meaningful AI-generation component judges
will look for on top of the rule-based detection.

CREDENTIALS: never hardcode your API key or project ID in this file.
Create a `.env` file (see .env.example and README.md) -- it's loaded
automatically below via python-dotenv, so you only set your credentials
once instead of retyping them every terminal session.
"""

import os
from dotenv import load_dotenv
from analyzer import Issue

load_dotenv()  # reads .env in the project folder and sets os.environ from it

USE_GRANITE = True  # flip to True once your .env file is set up (see README.md)

WATSONX_MODEL_ID = "ibm/granite-4-h-small"

FIX_SUGGESTIONS = {
    "nested_loop": "Consider whether the inner loop can be replaced with a set/dict lookup, "
                    "a vectorized operation (numpy/pandas), or a different algorithm to avoid O(n^2)+ cost.",
    "range_len": "Use `enumerate(x)` instead of `range(len(x))` for the same result with a small efficiency gain.",
    "string_concat_in_loop": "If this builds a string, collect pieces in a list and use `''.join(list)` once "
                              "after the loop instead of repeated `+=`.",
    "unmemoized_recursion": "Add `@lru_cache(maxsize=None)` (or `@cache` in Python 3.9+) above the function "
                             "definition to avoid recomputing overlapping subproblems.",
    "pandas_iterrows": "Replace the row-by-row loop with a vectorized pandas operation, e.g. "
                        "`df['col'].sum()` or `df.apply(...)` where possible.",
    "growing_list_len_check": "Precompute the target length before the loop, or restructure as a for-loop "
                               "over a fixed-size range.",
    "list_for_reduction": "Drop the square brackets — `sum(x*x for x in numbers)` is a generator and avoids "
                           "building the full intermediate list in memory.",
}


def generate_issue_explanation(issue: Issue) -> str:
    """TEMPLATE MODE explanation for a single issue, for use in plain-text
    reports (generate_full_report). Includes line/severity prefix."""
    fix = FIX_SUGGESTIONS.get(issue.pattern, "Review this line for a more efficient alternative.")
    return f"Line {issue.line} ({issue.severity.upper()}): {issue.detail} Suggested fix: {fix}"


def generate_issue_explanation_for_card(issue: Issue) -> str:
    """Same explanation, but WITHOUT the line/severity prefix -- for use in
    the app.py UI cards, which already render the line number and severity
    badge separately. Avoids the duplicated "Line X ... Line X" bug."""
    fix = FIX_SUGGESTIONS.get(issue.pattern, "Review this line for a more efficient alternative.")
    return f"{issue.detail} Suggested fix: {fix}"


def generate_full_report(issues: list[Issue], score_info: dict) -> str:
    """TEMPLATE MODE full report combining score + all issue explanations."""
    header = (
        f"Green Efficiency Score: {score_info['score']}/100 "
        f"(Estimated relative energy impact: {score_info['impact_level']}). "
        f"{score_info['summary']}"
    )
    if not issues:
        return header + " No specific issues detected in this scan."

    lines = [header, "", "Findings:"]
    for issue in issues:
        lines.append(f"- {generate_issue_explanation(issue)}")
    return "\n".join(lines)


def _get_granite_model():
    """
    Builds and returns an IBM watsonx.ai Granite model client, reading
    credentials from environment variables (never hardcoded -- see README).

    Required environment variables:
      WATSONX_API_KEY   -- your IBM Cloud API key
      WATSONX_PROJECT_ID -- your watsonx.ai project ID
      WATSONX_URL       -- your region endpoint, e.g. https://eu-de.ml.cloud.ibm.com
    """
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    api_key = os.environ.get("WATSONX_API_KEY")
    project_id = os.environ.get("WATSONX_PROJECT_ID")
    url = os.environ.get("WATSONX_URL", "https://eu-de.ml.cloud.ibm.com")

    if not api_key or not project_id:
        raise RuntimeError(
            "Missing WATSONX_API_KEY or WATSONX_PROJECT_ID environment variables. "
            "See README.md for how to set these before running with USE_GRANITE = True."
        )

    credentials = Credentials(url=url, api_key=api_key)

    return ModelInference(
        model_id=WATSONX_MODEL_ID,
        credentials=credentials,
        project_id=project_id,
        params={
            "decoding_method": "greedy",
            "max_new_tokens": 350,
            "min_new_tokens": 20,
            "repetition_penalty": 1.05,
        },
    )


def generate_full_report_granite(issues: list[Issue], score_info: dict) -> str:
    """
    GRANITE MODE -- real IBM watsonx.ai call. The prompt is explicitly
    grounded in the analyzer's actual findings (issues_text below) so
    Granite explains real detections rather than inventing new ones --
    this grounding is what makes it "RAG-adjacent" generation rather than
    free-floating hallucination.
    """
    if not issues:
        return (
            f"Green Efficiency Score: {score_info['score']}/100. "
            f"No specific issues detected in this scan."
        )

    issues_text = "\n".join(
        f"- Line {i.line} ({i.severity}): {i.detail}" for i in issues
    )

    prompt = f"""You are a helpful code reviewer focused on energy-efficient, sustainable coding practices.

A static analyzer found the following issues in a Python file (do not invent any additional issues beyond these):
{issues_text}

Overall Green Efficiency Score: {score_info['score']}/100 (estimated relative energy impact: {score_info['impact_level']}).

Write a short, friendly summary (4-6 sentences) for a student developer. Prioritize the highest-severity issues first. Be specific about why each pattern costs extra compute/energy, and keep the tone encouraging, not preachy."""

    model = _get_granite_model()
    response = model.generate_text(prompt=prompt)
    return response.strip()


def generate_full_report_auto(issues: list[Issue], score_info: dict) -> str:
    if USE_GRANITE:
        try:
            return generate_full_report_granite(issues, score_info)
        except Exception as e:
            # Fail gracefully to template mode rather than crashing the demo --
            # important for a live presentation where network/API issues can happen.
            return (
                f"[Granite call failed, showing template fallback: {e}]\n\n"
                + generate_full_report(issues, score_info)
            )
    return generate_full_report(issues, score_info)


if __name__ == "__main__":
    from analyzer import analyze_code
    from carbon_score import compute_score

    with open("sample_code/inefficient_example.py") as f:
        code = f.read()
    issues = analyze_code(code)
    score_info = compute_score(issues)
    print(generate_full_report_auto(issues, score_info))