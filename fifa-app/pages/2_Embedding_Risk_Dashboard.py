"""
Embedding Risk Dashboard - OOD detection, bias audit, stability
tests, temporal validation, and the SR 26-2 model card.

Reads pre-computed CSV/report artifacts. Adjust paths in the
load functions to match your local project layout.
"""
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Embedding Risk Dashboard",
                    page_icon="🛡️", layout="wide")

import os
_SECRET = None
try:
    _SECRET = st.secrets.get("PROJECT_ROOT", None)
except Exception:
    pass
ROOT = Path(_SECRET) if _SECRET else Path(r"C:\Users\manal\fifa-embedding-risk")
REPORTS = ROOT / "outputs" / "reports"

st.title("️ Embedding Risk Dashboard")
st.caption("Everything we found when we stress-tested the model "
           "before trusting it with live predictions.")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📉 Temporal Validation", "🌍 OOD & Bias",
     "📊 Stability", "📋 Model Card"]
)

# ── TAB 1: Temporal validation ──
with tab1:
    st.subheader("Train → In-Time → Out-of-Time")
    st.write(
        "We never let the model see the future. Training stops "
        "at end of 2023; In-Time covers 2024 through May 2026; "
        "Out-of-Time is the actual 2026 World Cup."
    )

    perf_df = pd.DataFrame({
        "Period": ["Train (2010-2023)", "In-Time (2024-May 2026)",
                   "OOT Base (WC 2026)", "OOT V5+Adjustments"],
        "Samples": [8701, 1591, 32, 32],
        "Accuracy": [0.825, 0.554, 0.531, 0.710],
        "AUC (macro)": [0.952, 0.721, 0.614, None],
        "F1 (macro)": [0.819, 0.506, 0.492, None],
        "Home Win F1": [0.847, 0.686, 0.533, 0.77],
        "Draw F1": [0.784, 0.286, 0.143, 0.33],
        "Away Win F1": [0.828, 0.546, 0.800, 1.00],
    })

    st.dataframe(
        perf_df.style.format({
            "Accuracy": "{:.1%}", "AUC (macro)": "{:.3f}",
            "F1 (macro)": "{:.3f}", "Home Win F1": "{:.0%}",
            "Draw F1": "{:.0%}", "Away Win F1": "{:.0%}",
        }, na_rep="-"),
        use_container_width=True, hide_index=True,
    )

    st.bar_chart(perf_df.set_index("Period")["Accuracy"])

    c1, c2 = st.columns(2)
    with c1:
        st.warning(
            "**Train → In-Time gap: −27.1 points**\n\n"
            "The model overfits 2010-2023 patterns. FIFA 22 "
            "embeddings (2021 player data) go stale for 2024+ "
            "matches - this is concept drift, not a bug."
        )
    with c2:
        st.success(
            "**OOT recovers to 71.0% with live adjustments**\n\n"
            "Baking in WC tournament form, FanDuel odds, and "
            "injury/suspension flags closes most of the gap - "
            "the static embeddings aren't the whole story."
        )

    st.markdown("**Per-class breakdown (OOT V5+Adjustments)**")
    bc1, bc2, bc3 = st.columns(3)
    bc1.metric("Home Win", "77%", "10/13 correct")
    bc2.metric("Away Win", "100%", "9/9 correct")
    bc3.metric("Draw", "33%", "3/9 correct - known weak spot")

# ── TAB 2: OOD & Bias ──
with tab2:
    st.subheader("Out-of-Distribution Detection")
    st.write(
        "Mahalanobis distance flags teams whose squad embeddings "
        "sit far outside the training distribution - predictions "
        "for these teams carry extra uncertainty."
    )

    ood_summary = pd.DataFrame({
        "Metric": ["Teams flagged as OOD", "Total WC teams",
                   "OOD threshold (85th percentile)",
                   "Example: Qatar"],
        "Value": ["26", "168 (full embedding set)", "Mahalanobis = 10.10",
                  "No FIFA squad data → AFC confederation mean fallback, flagged OOD"],
    })
    st.table(ood_summary)

    st.divider()
    st.subheader("Confederation Bias Audit")
    st.write(
        "We measured embedding quality gap by confederation - "
        "how much worse is representation for some regions "
        "versus others?"
    )

    bias_df = pd.DataFrame({
        "Confederation": ["CAF (Africa)", "AFC (Asia)", "CONCACAF",
                          "CONMEBOL", "UEFA"],
        "Representation Gap": [-0.371, -0.18, -0.09, -0.02, 0.00],
    }).sort_values("Representation Gap")

    st.bar_chart(bias_df.set_index("Confederation"))

    st.error(
        "**Root cause:** sparse player trait/attribute data for "
        "African players in the FIFA 22 source dataset. "
        "**Mitigation applied:** text enrichment using numeric "
        "attributes (pace, shooting, passing, etc.) to compensate "
        "for missing trait tags - reduced but did not eliminate "
        "the gap."
    )

# ── TAB 3: Stability ──
with tab3:
    st.subheader("Embedding Stability Under Perturbation")
    st.write(
        "If we slightly perturb a team's input embedding, how "
        "often does the model's predicted class flip? High "
        "flip rates would mean the model is brittle."
    )

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Mean cosine similarity (perturbed vs original)",
               "0.9897")
    sc2.metric("Prediction flip rate", "4.60%", "✅ stable")
    sc3.metric("PCA compression", "384 → 66 dims",
               "−0.3% accuracy loss")

    st.success(
        "A 4.6% flip rate under perturbation is low - the model's "
        "decisions are not hypersensitive to small embedding "
        "noise. PCA compression to 66 dimensions (95% variance "
        "retained) costs almost no accuracy while removing "
        "multicollinearity."
    )

# ── TAB 4: Model card ──
with tab4:
    st.subheader("Model Card")
    st.caption("Documentation aligned to SR 26-2 supervisory "
               "guidance on AI/ML model risk management.")

    st.markdown("""
**Model name:** FIFA Embedding Risk - V5 Match Predictor
**Model type:** Gradient-boosted classifier (XGBoost) on
sentence-embedding-derived features
**Intended use:** Match outcome prediction (Home Win / Draw /
Away Win) for international football, demonstrated on the
2026 FIFA World Cup
**Out of scope:** Club football, betting decisions, any use
where a 71% (and 33% on draws) accuracy ceiling is unacceptable
""")

    st.markdown("**Training data**")
    st.write(
        "- 10,434 international matches, 2010-2023 (training), "
        "2024-May 2026 (in-time validation)\n"
        "- 23,803 FIFA 22 player records → 384-dim text embeddings "
        "(sentence-transformers, all-MiniLM-L6-v2)\n"
        "- FIFA world rankings, 1992-2024"
    )

    st.markdown("**Known limitations**")
    st.write(
        "- Draw class is the model's weakest point "
        "(F1 = 0.143 base OOT, 0.33 with adjustments)\n"
        "- Embeddings are frozen at FIFA 22 (2021 squad data) - "
        "no mechanism to reflect 2024+ transfers or form "
        "changes without the live adjustment layer\n"
        "- Confederation bias: CAF nations have a measurable "
        "representation gap (−0.371) traced to sparse source data\n"
        "- 26 of 168 teams are flagged OOD; predictions for "
        "these teams should be treated with added caution"
    )

    st.markdown("**Monitoring & governance**")
    st.write(
        "- **Alert threshold:** OOT accuracy < 50% triggers "
        "review\n"
        "- **Human review required** for draw predictions and "
        "any OOD-flagged matchup\n"
        "- **Re-validation cadence:** before each major tournament, "
        "and whenever a new FIFA dataset becomes available\n"
        "- **Change log:** V1 (embeddings only, 46.9% OOT) → "
        "V2 (+form/draw detector, 65.6%) → V3 (+H2H/comp form) → "
        "V4 (+odds/injuries, 68.8%) → V5 (features trained "
        "end-to-end, 71.0%)"
    )

    st.info(
        "This model card documents known risks rather than "
        "hiding them - the goal is a system stakeholders can "
        "calibrate their trust in, not one presented as flawless."
    )
