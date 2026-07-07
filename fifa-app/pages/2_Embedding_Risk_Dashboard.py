"""
Embedding Risk Dashboard — validation metrics, OOD, bias, stability, model card.
Now includes live per-round tournament accuracy updated automatically.
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="Embedding Risk Dashboard",
                    page_icon="Shield", layout="wide")

st.title("Embedding Risk Dashboard")
st.caption("Everything we found when we stress-tested the model before trusting it with live predictions.")

# ── Load live accuracy ──
live_accuracy = None
try:
    from live_data import get_live_data, compute_round_accuracy
    data = get_live_data()
    live_accuracy = compute_round_accuracy(data)
except Exception as e:
    st.caption(f"Live accuracy unavailable: {e}")

tab1, tab2, tab3, tab4 = st.tabs([
    "Temporal Validation", "OOD and Bias", "Stability", "Model Card"
])

# ── TAB 1: TEMPORAL VALIDATION ──
with tab1:
    st.subheader("Train to In-Time to Out-of-Time")
    st.write(
        "We never let the model see the future. Training stops at end of 2023; "
        "In-Time covers 2024 through May 2026; Out-of-Time is the actual 2026 World Cup."
    )

    perf_df = pd.DataFrame({
        "Period": ["Train (2010-2023)", "In-Time (2024-May 2026)",
                   "OOT Base (WC 2026)", "OOT V5+Adjustments"],
        "Model":  ["V5 base","V5 base","V5 base","V5+Adj"],
        "Samples":[8701,1591,32,32],
        "Accuracy":[0.825,0.554,0.531,0.710],
        "AUC":    [0.952,0.721,0.614,None],
        "F1":     [0.819,0.506,0.492,None],
        "Home Win F1":[0.847,0.686,0.533,0.77],
        "Draw F1":    [0.784,0.286,0.143,0.33],
        "Away Win F1":[0.828,0.546,0.800,1.00],
    })

    st.dataframe(
        perf_df.style.format({
            "Accuracy":"{:.1%}","AUC":"{:.3f}","F1":"{:.3f}",
            "Home Win F1":"{:.0%}","Draw F1":"{:.0%}","Away Win F1":"{:.0%}",
        }, na_rep="-"),
        use_container_width=True, hide_index=True,
    )
    st.bar_chart(perf_df.set_index("Period")["Accuracy"])

    st.divider()

    # ── LIVE TOURNAMENT ACCURACY BY ROUND ──
    st.subheader("Live Tournament Accuracy by Round")
    st.caption("Updates automatically as matches complete. Refresh page for latest.")

    if live_accuracy:
        # Summary metrics
        overall = live_accuracy.get("Overall",{})
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Overall Accuracy",
                  f"{overall.get('accuracy',0):.1f}%",
                  f"{overall.get('correct',0)}/{overall.get('total',0)} correct")
        m2.metric("Group Stage",
                  f"{live_accuracy.get('Group Stage',{}).get('accuracy',0):.1f}%")
        m3.metric("Round of 32",
                  f"{live_accuracy.get('Round of 32',{}).get('accuracy',0):.1f}%")
        m4.metric("Round of 16",
                  f"{live_accuracy.get('Round of 16',{}).get('accuracy',0):.1f}%")

        # Per-round table
        round_rows = []
        for round_name in ["Group Stage","Round of 32","Round of 16",
                           "Quarterfinals","Semifinals","Final"]:
            stats = live_accuracy.get(round_name)
            if stats and stats["total"] > 0:
                round_rows.append({
                    "Round":    round_name,
                    "Correct":  stats["correct"],
                    "Total":    stats["total"],
                    "Accuracy": f"{stats['accuracy']:.1f}%",
                })

        if round_rows:
            round_df = pd.DataFrame(round_rows)
            st.dataframe(round_df, use_container_width=True, hide_index=True)

        # Bar chart
        chart_data = {r["Round"]: float(r["Accuracy"].replace("%",""))/100
                      for r in round_rows}
        if chart_data:
            st.bar_chart(chart_data)

        # R32 match-by-match breakdown
        with st.expander("Round of 32 — match by match breakdown"):
            r32_stats = live_accuracy.get("Round of 32",{}).get("results",[])
            if r32_stats:
                for r in r32_stats:
                    check = "correct" if r.get("correct") else "missed"
                    method = r.get("method","")
                    upset  = not r.get("correct",True)
                    color  = "#ff6666" if upset else "#4A90D9"
                    st.markdown(
                        f"<div style='font-size:13px;padding:2px 0'>"
                        f"<span style='color:{color}'>"
                        f"{'UPSET ' if upset else ''}"
                        f"{r['home']} vs {r['away']}: "
                        f"<b>{r['winner']}</b> wins"
                        f"{' (' + method + ')' if method != '90min' else ''}"
                        f" - Model {check}</span></div>",
                        unsafe_allow_html=True
                    )

        # R16 breakdown
        with st.expander("Round of 16 — match by match breakdown"):
            r16_stats = live_accuracy.get("Round of 16",{}).get("results",[])
            if r16_stats:
                for r in r16_stats:
                    check = "correct" if r.get("correct") else "missed"
                    upset  = not r.get("correct",True)
                    color  = "#ff6666" if upset else "#4A90D9"
                    st.markdown(
                        f"<div style='font-size:13px;padding:2px 0'>"
                        f"<span style='color:{color}'>"
                        f"{'UPSET ' if upset else ''}"
                        f"{r['home']} vs {r['away']}: "
                        f"<b>{r['winner']}</b>"
                        f" - Model {check}</span></div>",
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No R16 results yet or live data unavailable.")

    else:
        st.info("Live accuracy will appear here as matches complete.")

    st.divider()
    c1,c2 = st.columns(2)
    with c1:
        st.warning(
            "**Train to In-Time gap: -27.1 points**\n\n"
            "FIFA 22 embeddings (2021 data) go stale for 2024+ matches — concept drift."
        )
    with c2:
        st.success(
            "**OOT recovers to 71.0% with live adjustments**\n\n"
            "WC tournament form + FanDuel odds + injury flags close most of the gap."
        )

    st.markdown("**Per-class breakdown (Group Stage OOT V5+Adj)**")
    bc1,bc2,bc3 = st.columns(3)
    bc1.metric("Home Win","77%","10/13 correct")
    bc2.metric("Away Win","100%","9/9 correct")
    bc3.metric("Draw","33%","3/9 correct - known weak spot")

# ── TAB 2: OOD and BIAS ──
with tab2:
    st.subheader("Out-of-Distribution Detection")
    st.write(
        "Mahalanobis distance flags teams whose squad embeddings sit far outside "
        "the training distribution."
    )
    ood_df = pd.DataFrame({
        "Metric":["Teams flagged as OOD","Total WC teams",
                  "OOD threshold (85th pct)","Example: Qatar"],
        "Value": ["26","168 (full embedding set)","Mahalanobis = 10.10",
                  "No FIFA squad data - AFC mean fallback, flagged OOD"],
    })
    st.table(ood_df)

    st.divider()
    st.subheader("Confederation Bias Audit")
    bias_df = pd.DataFrame({
        "Confederation":["CAF (Africa)","AFC (Asia)","CONCACAF","CONMEBOL","UEFA"],
        "Representation Gap":[-0.371,-0.18,-0.09,-0.02,0.00],
    }).sort_values("Representation Gap")
    st.bar_chart(bias_df.set_index("Confederation"))
    st.error(
        "**Root cause:** sparse player trait data for African players in FIFA 22. "
        "**Mitigation:** text enrichment using numeric attributes reduced but did not eliminate the gap."
    )

# ── TAB 3: STABILITY ──
with tab3:
    st.subheader("Embedding Stability Under Perturbation")
    sc1,sc2,sc3 = st.columns(3)
    sc1.metric("Mean cosine similarity (perturbed vs original)","0.9897")
    sc2.metric("Prediction flip rate","4.60%","stable")
    sc3.metric("PCA compression","384 to 66 dims","-0.3% accuracy loss")
    st.success(
        "A 4.6% flip rate under perturbation is low — the model is not "
        "hypersensitive to small embedding noise."
    )

# ── TAB 4: MODEL CARD ──
with tab4:
    st.subheader("Model Card")
    st.caption("SR 26-2 aligned documentation.")

    st.markdown("""
**Model name:** FIFA 2026 Match Prediction - V5
**Model type:** XGBoost on sentence-embedding-derived features
**Intended use:** Match outcome prediction for international football, demonstrated on 2026 World Cup
**Out of scope:** Club football, betting decisions, any use where 71% accuracy is unacceptable
""")

    st.markdown("**Training data**")
    st.write(
        "- 10,434 international matches, 2010-2023 (training), 2024-May 2026 (in-time)\n"
        "- 23,803 FIFA 22 players -> 384-dim embeddings (all-MiniLM-L6-v2)\n"
        "- FIFA world rankings 1992-2024"
    )

    st.markdown("**Known limitations**")
    st.write(
        "- Draw class is weakest (F1=0.143 base OOT, 0.33 with adjustments)\n"
        "- Embeddings frozen at FIFA 22 (2021) - staleness grows over time\n"
        "- CAF bias: -0.371 representation gap documented\n"
        "- 26/168 teams flagged OOD - treat predictions with added caution\n"
        "- Knockout upsets (Norway beating Brazil, Morocco beating Netherlands) "
        "show model struggles with momentum and tactical outliers"
    )

    st.markdown("**Monitoring and governance**")
    st.write(
        "- Alert threshold: OOT accuracy < 50% triggers review\n"
        "- Human review required for draw predictions and OOD matchups\n"
        "- Re-validation recommended before each major tournament\n"
        "- Live per-round accuracy tracked in Temporal Validation tab above"
    )

    if live_accuracy:
        overall = live_accuracy.get("Overall",{})
        st.info(
            f"**Current live accuracy: {overall.get('accuracy',0):.1f}%** "
            f"({overall.get('correct',0)}/{overall.get('total',0)} matches correct "
            f"across all completed knockout rounds)"
        )
