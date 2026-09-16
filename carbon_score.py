"""
carbon_score.py
---------------
Converts the raw list of detected issues into:
1. A 0-100 "Green Efficiency Score"
2. A relative energy-impact estimate (Low / Medium / High)

IMPORTANT HONESTY NOTE (put this in your Responsible AI slide too):
This is a RELATIVE, educational estimate based on known algorithmic
complexity anti-patterns -- it is NOT a measured, calibrated energy/CO2
number. Real energy measurement would need actual profiling (e.g. tools
like CodeCarbon) on real hardware. We are transparent about this
limitation rather than presenting a fake-precise number.
"""

from analyzer import Issue, PATTERN_WEIGHTS


def compute_score(issues: list[Issue]) -> dict:
    total_penalty = sum(PATTERN_WEIGHTS.get(i.pattern, 10) for i in issues)
    score = max(0, 100 - total_penalty)

    if score >= 85:
        impact_level = "Low"
        summary = "This code shows few or no known energy-inefficient patterns."
    elif score >= 60:
        impact_level = "Medium"
        summary = "This code has some patterns that add avoidable compute cost, worth fixing before scaling up."
    else:
        impact_level = "High"
        summary = "This code has multiple patterns that could meaningfully waste compute (and energy) at scale."

    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        severity_counts[issue.severity] += 1

    return {
        "score": score,
        "impact_level": impact_level,
        "summary": summary,
        "total_issues": len(issues),
        "severity_counts": severity_counts,
    }


if __name__ == "__main__":
    from analyzer import analyze_code

    with open("sample_code/inefficient_example.py") as f:
        code = f.read()
    issues = analyze_code(code)
    result = compute_score(issues)
    print(result)
