"""
FIFA Embedding Risk - Main App Entry Point
A Football Match Prediction System: Built, Questioned, Trusted

Run with: streamlit run Home.py
"""
import streamlit as st

st.set_page_config(
    page_title="FIFA Embedding Risk",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4A90D9, #4CAF50);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .subtitle {
        font-size: 1.15rem;
        color: #9aa0a6;
        margin-top: 0;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #1e2530;
        border-radius: 12px;
        padding: 1.2rem;
        border-left: 5px solid #4A90D9;
        color: #e8eaed;
    }
    .act-card {
        background: #1e2530;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #333a45;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        color: #e8eaed;
    }
    .act-card h4 {
        color: #ffffff;
        margin-top: 0.3rem;
        margin-bottom: 0.6rem;
    }
    .act-card p {
        color: #c4c9d0;
        line-height: 1.5;
    }
    .act-card i {
        color: #e8eaed;
    }
    .act-number {
        font-size: 0.85rem;
        font-weight: 700;
        color: #1B8A4C;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ──
st.markdown('<p class="main-header">⚽ FIFA Embedding Risk</p>',
            unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">A football match prediction system - '
    'built, questioned, and stress-tested before going live on '
    'the 2026 World Cup.</p>',
    unsafe_allow_html=True
)

st.divider()

# ── Hero metrics ──
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("OOT Accuracy (V5+Adj)", "71.0%", "+24.1% vs base")
with c2:
    st.metric("Players Embedded", "23,803", "384-dim vectors")
with c3:
    st.metric("SAE Concepts Found", "87", "of 512 dimensions")
with c4:
    st.metric("WC Matches Predicted", "104", "Group → Final")

st.divider()

# ── The story ──
st.subheader("The Story")
st.write(
    "We started with a simple question: *can FIFA player "
    "descriptions predict international match outcomes?* "
    "Getting to a system we could defend meant building it, "
    "then questioning it, then stress-testing it before letting "
    "it make live predictions on the 2026 World Cup."
)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
<div class="act-card">
<p class="act-number">Act 1 - Build</p>
<h4>Can embeddings predict match outcomes?</h4>
<p>Text → sentence-transformer embeddings → XGBoost.
The baseline system works: 52.9% accuracy, well above the
33% random baseline for a 3-class problem.</p>
</div>

<div class="act-card">
<p class="act-number">Act 2 - Question</p>
<h4>What is the model actually learning?</h4>
<p>SHAP shows raw embedding dimensions are uninterpretable.
Probing classifiers reveal position (95.3%), preferred foot
(85.0%), and rating tier (72.6%) are all strongly encoded -
just not in any single dimension we can read.</p>
</div>

<div class="act-card">
<p class="act-number">Act 3 - Stress Test</p>
<h4>When does the model fail?</h4>
<p>Mahalanobis OOD detection flags 26 of 168 teams as outside
the training distribution. A bias audit finds a -0.371
representation gap for CAF (African) nations. Temporal
validation shows accuracy drops from 82.5% (train) to 53.1%
(out-of-time) - real concept drift, fully documented.</p>
</div>
""", unsafe_allow_html=True)

with col2:
    st.markdown("""
<div class="act-card">
<p class="act-number">Act 4 - Improve</p>
<h4>Building a system we can defend</h4>
<p>V5 bakes head-to-head history and competitive form directly
into training. Live adjustments blend in tournament form,
FanDuel odds, and injury/suspension flags. Result: 71.0% OOT
accuracy, with known weaknesses (draws, F1=0.143) documented
rather than hidden.</p>
</div>

<div class="act-card">
<p class="act-number">Act 5 - Deploy</p>
<h4>Real predictions, public accountability</h4>
<p>Every Round of 32 through Final prediction is logged with
its confidence score and the caveats that go with it. The
model goes on record for the 2026 World Cup - explore its
calls in the Bracket and Match Predictor pages.</p>
</div>

<div class="metric-card">
<b>🔬 The interpretability layer</b><br>
A Sparse Autoencoder trained on all 23,803 player embeddings
surfaces 87 monosemantic football concepts out of 512
dimensions - things like <i>"Creative Playmaker"</i> and
<i>"Commanding CB (Italian)"</i> - discovered without ever
telling the model what a center-back is.
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Navigation guide ──
st.subheader("Explore the System")
nc1, nc2, nc3 = st.columns(3)
with nc1:
    st.info("** Match Predictor**\n\nPick any two national teams "
            "and get a live V5 prediction with full feature "
            "breakdown.")
with nc2:
    st.info("** WC 2026 Bracket**\n\nThe full Round of 32 → Final "
            "simulation, updated as real results come in.")
with nc3:
    st.info("** Player DNA Explorer**\n\nSearch any player, see "
            "which of the 87 SAE concepts activate for them.")

nc4, nc5 = st.columns(2)
with nc4:
    st.info("** How It Works**\n\nThe full pipeline - probing "
            "results, SAE concept gallery, SHAP analysis.")
with nc5:
    st.info("**️ Embedding Risk Dashboard**\n\nOOD detection, "
            "bias audit, stability tests, and the SR 26-2 model "
            "card.")

st.divider()
st.caption(
    "Built with Python · XGBoost · PyTorch · sentence-transformers · "
    "SHAP · UMAP · Streamlit  -  "
    "[GitHub](https://github.com/yourusername/fifa-embedding-risk)"
)
