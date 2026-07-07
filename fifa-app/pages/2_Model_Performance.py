"""
Model Performance — validation metrics, live tournament accuracy by round,
OOD detection, bias audit, stability tests, and model card.
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="Model Performance",
                    page_icon="Chart", layout="wide")

st.title("Model Performance")
st.caption(
    "Validation metrics, live tournament accuracy, and everything we found "
    "when we stress-tested the model before trusting it with live predictions."
)

# Load live accuracy
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

with tab1:
    st.subheader("Train to In-Time to Out-of-Time")
    st.write(
        "We never let the model see the future. Training stops at end of 2023. "
        "In-Time covers 2024 through May 2026. "
        "Out-of-Time is the actual 2026 World Cup — matches the model never saw."
    )

    perf_df = pd.DataFrame({
        "Period":      ["Train (2010-2023)","In-Time (2024-May 2026)",
                        "OOT Base (WC 2026)","OOT V5+Adjustments"],
        "Model":       ["V5 base","V5 base","V5 base","V5+Adj"],
        "Samples":     [8701,1591,32,32],
        "Accuracy":    [0.825,0.554,0.531,0.710],
        "AUC":         [0.952,0.721,0.614,None],
        "F1":          [0.819,0.506,0.492,None],
        "Home Win F1": [0.847,0.686,0.533,0.77],
        "Draw F1":     [0.784,0.286,0.143,0.33],
        "Away Win F1": [0.828,0.546,0.800,1.00],
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
    st.subheader("Live Tournament Accuracy by Round")
    st.caption("Updates automatically every 15 minutes as matches complete via ESPN API.")

    if live_accuracy:
        overall = live_accuracy.get("Overall",{})
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Overall",
                  f"{overall.get('accuracy',0):.1f}%",
                  f"{overall.get('correct',0)}/{overall.get('total',0)} correct")
        m2.metric("Group Stage",
                  f"{live_accuracy.get('Group Stage',{}).get('accuracy',0):.1f}%")
        m3.metric("Round of 32",
                  f"{live_accuracy.get('Round of 32',{}).get('accuracy',0):.1f}%")
        m4.metric("Round of 16",
                  f"{live_accuracy.get('Round of 16',{}).get('accuracy',0):.1f}%")

        round_rows = []
        for rnd in ["Group Stage","Round of 32","Round of 16",
                    "Quarterfinals","Semifinals","Final"]:
            s = live_accuracy.get(rnd)
            if s and s["total"] > 0:
                round_rows.append({
                    "Round":    rnd,
                    "Correct":  s["correct"],
                    "Total":    s["total"],
                    "Accuracy": f"{s['accuracy']:.1f}%",
                })

        if round_rows:
            st.dataframe(pd.DataFrame(round_rows),
                        use_container_width=True, hide_index=True)
            chart = {r["Round"]: float(r["Accuracy"].replace("%",""))/100
                     for r in round_rows}
            st.bar_chart(chart)

        with st.expander("Round of 32 - match by match"):
            for r in live_accuracy.get("Round of 32",{}).get("results",[]):
                correct = r.get("correct", False)
                color   = "#4A90D9" if correct else "#ff6666"
                method  = r.get("method","")
                st.markdown(
                    f"<div style='font-size:13px;padding:2px 0;color:{color}'>"
                    f"{'UPSET ' if not correct else ''}"
                    f"{r['home']} vs {r['away']}: <b>{r['winner']}</b>"
                    f"{' (' + method + ')' if method != '90min' else ''}"
                    f" - {'correct' if correct else 'missed'}</div>",
                    unsafe_allow_html=True
                )

        with st.expander("Round of 16 - match by match"):
            r16 = live_accuracy.get("Round of 16",{}).get("results",[])
            if r16:
                for r in r16:
                    correct = r.get("correct", False)
                    color   = "#4A90D9" if correct else "#ff6666"
                    st.markdown(
                        f"<div style='font-size:13px;padding:2px 0;color:{color}'>"
                        f"{'UPSET ' if not correct else ''}"
                        f"{r['home']} vs {r['away']}: <b>{r['winner']}</b>"
                        f" - {'correct' if correct else 'missed'}</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No R16 results loaded yet.")
    else:
        st.info("Live accuracy loads automatically as matches complete.")

    st.divider()
    c1,c2 = st.columns(2)
    with c1:
        st.warning(
            "**Train to In-Time gap: -27.1 points**\n\n"
            "FIFA 22 embeddings (2021 data) go stale for 2024+ matches - concept drift."
        )
    with c2:
        st.success(
            "**OOT recovers to 71.0% with live adjustments**\n\n"
            "WC form + FanDuel odds + injury flags close most of the gap."
        )

    st.markdown("**Per-class breakdown (Group Stage OOT V5+Adj)**")
    bc1,bc2,bc3 = st.columns(3)
    bc1.metric("Home Win","77%","10/13 correct")
    bc2.metric("Away Win","100%","9/9 correct")
    bc3.metric("Draw","33%","3/9 correct - known weak spot")

with tab2:
    st.subheader("Out-of-Distribution Detection")
    st.write(
        "Mahalanobis distance flags teams whose squad embeddings sit far outside "
        "the training distribution. Predictions for these teams carry extra uncertainty."
    )
    st.table(pd.DataFrame({
        "Metric":["Teams flagged as OOD","Total WC teams",
                  "OOD threshold (85th pct)","Example: Qatar"],
        "Value": ["26","168 (full embedding set)","Mahalanobis = 10.10",
                  "No FIFA squad data - AFC mean fallback, flagged OOD"],
    }))

    st.divider()
    st.subheader("Confederation Bias Audit")
    bias_df = pd.DataFrame({
        "Confederation": ["CAF (Africa)","AFC (Asia)","CONCACAF","CONMEBOL","UEFA"],
        "Representation Gap": [-0.371,-0.18,-0.09,-0.02,0.00],
    }).sort_values("Representation Gap")
    st.bar_chart(bias_df.set_index("Confederation"))
    st.error(
        "**Root cause:** sparse player trait data for African players in FIFA 22. "
        "**Mitigation applied:** text enrichment using numeric attributes reduced "
        "but did not fully eliminate the gap."
    )

with tab3:
    st.subheader("Embedding Stability Under Perturbation")
    sc1,sc2,sc3 = st.columns(3)
    sc1.metric("Mean cosine similarity","0.9897","perturbed vs original")
    sc2.metric("Prediction flip rate","4.60%","stable")
    sc3.metric("PCA compression","384 to 66 dims","-0.3% accuracy loss")
    st.success(
        "4.6% flip rate under perturbation is low. "
        "PCA compression to 66 dimensions (95% variance retained) "
        "costs almost no accuracy while removing multicollinearity."
    )

with tab4:
    st.subheader("Model Card")
    st.caption("SR 26-2 aligned documentation.")

    st.markdown("""
**Model name:** FIFA 2026 Match Prediction - V5
**Model type:** XGBoost on sentence-embedding-derived features (78 features, temporal split)
**Intended use:** International football match outcome prediction, demonstrated on 2026 World Cup
**Out of scope:** Club football, betting decisions, any use where current accuracy ceiling is unacceptable
""")

    st.markdown("**Training data**")
    st.write(
        "- 10,434 international matches 2010-2023 (training) + 2024-May 2026 (in-time)\n"
        "- 23,803 FIFA 22 players encoded via sentence-transformers (all-MiniLM-L6-v2)\n"
        "- FIFA world rankings 1992-2024"
    )

    st.markdown("**Known limitations**")
    st.write(
        "- Draw class is weakest: F1=0.143 base OOT, 0.33 with live adjustments\n"
        "- Embeddings frozen at FIFA 22 (2021) - staleness grows over time\n"
        "- CAF confederation bias: -0.371 representation gap documented\n"
        "- 26/168 teams flagged OOD\n"
        "- Model struggles with tactical outliers and penalty shootout outcomes\n"
        "- Norway beating Brazil and Morocco beating Netherlands showed the limits "
        "of static squad quality embeddings vs live momentum signals"
    )

    st.markdown("**Monitoring and governance**")
    st.write(
        "- Alert threshold: OOT accuracy < 50% triggers review\n"
        "- Human review required for draw predictions and OOD matchups\n"
        "- Re-validation recommended before each major tournament\n"
        "- Live per-round accuracy tracked in Temporal Validation tab above\n"
        "- Change log: V1 (46.9%) -> V2 (65.6%) -> V3 (~67%) -> V4 (68.8%) -> V5 (71.0%)"
    )

    if live_accuracy:
        overall = live_accuracy.get("Overall",{})
        st.info(
            f"**Current live accuracy: {overall.get('accuracy',0):.1f}%** "
            f"({overall.get('correct',0)}/{overall.get('total',0)} matches correct "
            f"across all completed knockout rounds)"
        )
