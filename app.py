"""
app.py
------
GreenCode demo app — reskinned version. Run with: streamlit run app.py

Same backend logic as before (analyzer.py, carbon_score.py,
message_generator.py are untouched) — this file only changes the visual
layer: custom CSS theme, card-style metrics, colored severity badges,
and a cleaner overall layout.
"""

import streamlit as st

from analyzer import analyze_code
from carbon_score import compute_score
from message_generator import generate_issue_explanation_for_card, generate_full_report_auto, USE_GRANITE

st.set_page_config(page_title="GreenCode", page_icon="🌱", layout="wide")

# ------------------------------------------------------------------
# CUSTOM THEME
# ------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

html, body, [class*="css"]  {
    font-family: 'Poppins', sans-serif;
}

.stApp {
    background: linear-gradient(180deg, #f4faf6 0%, #eef7f1 100%);
}

.gc-header {
    background: linear-gradient(120deg, #1f8a5f 0%, #2fb872 60%, #7bd99a 100%);
    padding: 2rem 2.2rem;
    border-radius: 18px;
    color: white;
    margin-bottom: 1.6rem;
    box-shadow: 0 8px 24px rgba(31, 138, 95, 0.25);
}
.gc-header h1 {
    color: white;
    margin: 0;
    font-size: 2.1rem;
    font-weight: 700;
}
.gc-header p {
    color: #e6fbee;
    margin: 0.4rem 0 0 0;
    font-size: 0.95rem;
}

.gc-section-title {
    font-weight: 600;
    font-size: 1.15rem;
    color: #14532d;
    margin: 1.2rem 0 0.6rem 0;
}

.gc-metric-card {
    background: white;
    border-radius: 14px;
    padding: 1.1rem 1rem;
    text-align: center;
    box-shadow: 0 2px 10px rgba(20, 83, 45, 0.08);
    border: 1px solid #e3f2e8;
}
.gc-metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #14532d;
}
.gc-metric-label {
    font-size: 0.8rem;
    color: #5a7a68;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 0.2rem;
}
.gc-metric-card.impact-low .gc-metric-value { color: #1f8a5f; }
.gc-metric-card.impact-medium .gc-metric-value { color: #d98c1a; }
.gc-metric-card.impact-high .gc-metric-value { color: #cc3b3b; }

.badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    margin-right: 0.5rem;
}
.badge-high { background: #fde2e2; color: #b02a2a; }
.badge-medium { background: #fdf0da; color: #a6650b; }
.badge-low { background: #e3f2e8; color: #1f8a5f; }

.finding-card {
    background: white;
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.6rem;
    border-left: 4px solid #cfd8d3;
    box-shadow: 0 1px 6px rgba(20, 83, 45, 0.06);
}
.finding-card.sev-high { border-left-color: #cc3b3b; }
.finding-card.sev-medium { border-left-color: #d98c1a; }
.finding-card.sev-low { border-left-color: #1f8a5f; }
.finding-title {
    font-weight: 600;
    color: #14532d;
    margin-bottom: 0.25rem;
}
.finding-detail {
    color: #3b4a41;
    font-size: 0.9rem;
    line-height: 1.4;
}

div.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    border: 1px solid #cfe8d8;
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(120deg, #1f8a5f, #2fb872);
    border: none;
}

.gc-empty-state {
    background: white;
    border-radius: 14px;
    padding: 1.4rem;
    text-align: center;
    color: #5a7a68;
    border: 1px dashed #bcdccb;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------
st.markdown("""
<div class="gc-header">
    <h1>🌱 GreenCode — Carbon-Aware Code Review Assistant</h1>
    <p>SDG 13 · Climate Action &nbsp;·&nbsp; Static pattern detection + AI-generated explanations</p>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📊 About the score")
    st.write(
        "The Green Efficiency Score is a **relative, educational** estimate based on "
        "known algorithmic anti-patterns — not a measured energy/CO2 number. "
        "Real measurement would need hardware-level profiling (e.g. CodeCarbon)."
    )
    st.markdown("### 🔍 Patterns detected")
    for label in [
        "Nested loops (O(n²)+)",
        "`range(len(x))` instead of `enumerate`",
        "String concatenation in loops",
        "Unmemoized recursion",
        "`pandas.iterrows()`",
        "List built just to reduce (`sum([...])`)",
        "Growing-list `len()` recheck in while-loops",
    ]:
        st.markdown(f"- {label}")

# ------------------------------------------------------------------
# SAMPLE LOADERS + CODE INPUT
# ------------------------------------------------------------------
st.markdown('<div class="gc-section-title">Try it out</div>', unsafe_allow_html=True)
col_a, col_b = st.columns(2)
with col_a:
    if st.button("⚠️ Load inefficient sample", use_container_width=True):
        try:
            with open("sample_code/inefficient_example.py", encoding="utf-8") as f:
                st.session_state["code_input"] = f.read()
        except FileNotFoundError:
            st.error("Couldn't find sample_code/inefficient_example.py — check the file is in place.")
with col_b:
    if st.button("✅ Load efficient sample", use_container_width=True):
        try:
            with open("sample_code/efficient_example.py", encoding="utf-8") as f:
                st.session_state["code_input"] = f.read()
        except FileNotFoundError:
            st.error("Couldn't find sample_code/efficient_example.py — check the file is in place.")

code_input = st.text_area(
    "Paste your Python code here:",
    value=st.session_state.get("code_input", ""),
    height=280,
)

analyze_clicked = st.button("🔎 Analyze", type="primary", use_container_width=False)

# ------------------------------------------------------------------
# RESULTS
# ------------------------------------------------------------------
if analyze_clicked and not code_input.strip():
    st.warning("Paste some code (or load a sample) before clicking Analyze.")

elif analyze_clicked and code_input.strip():
    try:
        issues = analyze_code(code_input)
        score_info = compute_score(issues)
        impact_class = f"impact-{score_info['impact_level'].lower()}"

        st.markdown('<div class="gc-section-title">Results</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        metrics = [
            (c1, f"{score_info['score']}/100", "Green Efficiency Score", impact_class),
            (c2, score_info["impact_level"], "Estimated Impact", impact_class),
            (c3, score_info["total_issues"], "Issues Found", ""),
            (c4, score_info["severity_counts"]["high"], "High Severity", ""),
        ]
        for col, value, label, extra_class in metrics:
            with col:
                st.markdown(f"""
                <div class="gc-metric-card {extra_class}">
                    <div class="gc-metric-value">{value}</div>
                    <div class="gc-metric-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.info(score_info["summary"])

        st.markdown('<div class="gc-section-title">AI-Generated Summary</div>', unsafe_allow_html=True)
        with st.spinner("Generating summary..." if USE_GRANITE else "Building summary..."):
            ai_summary = generate_full_report_auto(issues, score_info)
        st.markdown(f"""
        <div class="finding-card">
            <div class="finding-detail">{ai_summary}</div>
        </div>
        """, unsafe_allow_html=True)
        if not USE_GRANITE:
            st.caption("Running in template mode. Set USE_GRANITE = True in message_generator.py "
                       "(with your watsonx credentials as environment variables) for real IBM Granite generation.")

        if issues:
            st.markdown('<div class="gc-section-title">Findings</div>', unsafe_allow_html=True)
            for issue in issues:
                badge_class = f"badge-{issue.severity}"
                card_class = f"sev-{issue.severity}"
                title = issue.pattern.replace("_", " ").title()
                explanation = generate_issue_explanation_for_card(issue)
                st.markdown(f"""
                <div class="finding-card {card_class}">
                    <div class="finding-title">
                        <span class="badge {badge_class}">{issue.severity}</span>
                        Line {issue.line} — {title}
                    </div>
                    <div class="finding-detail">{explanation}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No known inefficient patterns detected in this scan. 🎉")

    except SyntaxError as e:
        st.error(f"Couldn't parse this code — check for a syntax error: {e}")

elif not code_input.strip():
    st.markdown("""
    <div class="gc-empty-state">
        👆 Load a sample above, or paste your own Python code, then click <b>Analyze</b>.
    </div>
    """, unsafe_allow_html=True)