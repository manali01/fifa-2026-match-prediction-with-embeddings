"""
How It Works - pipeline walkthrough, probing results, SHAP
summary, SAE concept gallery.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="How It Works", page_icon="",
                    layout="wide")

st.title(" How the Model Works")
st.caption("The full pipeline, from raw text to live predictions.")

st.subheader("Pipeline")
st.markdown("""
```
Player text                "RW, pacey winger, clinical finisher,
                             88 OVR, Brazil, right foot"
      │
      ▼
sentence-transformers       all-MiniLM-L6-v2 → 384-dim vector
      │
      ▼
Mean-pool top 26 per nation → 384-dim team embedding
      │
      ▼
PCA (66 dims, 95% var)      removes multicollinearity
      │
      ▼
V5 feature vector            78 features: PCA dims + rankings +
                              H2H + competitive form + similarity
      │
      ▼
XGBoost (V5)                 300 trees, depth 5, temporal split
      │
      ▼
Live adjustment layer        WC tournament form + FanDuel odds +
                              injury/suspension flags
      │
      ▼
Final prediction              Home Win / Draw / Away Win + confidence
```
""")

st.divider()

st.subheader("Probing Classifiers: What's Hiding in the Embeddings")
st.write(
    "Raw embedding dimensions are individually meaningless - SHAP "
    "confirms this. But training simple classifiers to predict "
    "known attributes *from* the embeddings reveals the "
    "information is there, just entangled across many dimensions."
)

probing_df = pd.DataFrame({
    "Concept": ["Position", "Attacking Profile", "Preferred Foot",
               "Work Rate", "Physical Profile", "Rating Tier"],
    "Probe Accuracy": [0.953, 0.878, 0.850, 0.786, 0.776, 0.726],
})
st.bar_chart(probing_df.set_index("Concept"))
st.caption(
    "All probes scored well above chance, but pairwise "
    "correlations between probe accuracy and the match-prediction "
    "model's own feature importance were near zero - the "
    "downstream model exploits dimensions that don't map cleanly "
    "onto any single known football concept. That gap is exactly "
    "what the Sparse Autoencoder was built to close."
)

st.divider()

st.subheader("SAE Concept Gallery (sample)")
st.write(
    "A sample of the 87 monosemantic concepts the Sparse "
    "Autoencoder discovered, named by inspecting each "
    "dimension's top-activating players."
)

sae_sample = pd.DataFrame({
    "Dimension": [76, 188, 2, 307, 51],
    "Concept": ["Solid Defender (Italy)", "Solid Defender (Netherlands)",
               "Balanced Midfielder", "Attacking Player (pacey)",
               "Attacking Player"],
    "Top Players (sample)": [
        "Bonucci, Di Lorenzo, De Sciglio",
        "D. Sánchez, van den Berg ×3",
        "-", "-", "-",
    ],
    "Activation Frequency": ["62.7%", "66.0%", "47.5%", "60.1%", "63.6%"],
})
st.dataframe(sae_sample, use_container_width=True, hide_index=True)

st.info(
    "A notable finding: many SAE dimensions cluster by "
    "**nationality and playing style together** - e.g. one "
    "dimension activates almost exclusively for Italian center-"
    "backs, another for Dutch ones. The model learned that "
    "national footballing styles are a coherent, separable "
    "signal, without ever being told nationality mattered."
)

st.divider()

st.subheader("UMAP: Embedding Space at a Glance")
st.write(
    "Projecting the 384-dim player embeddings down to 2D with "
    "UMAP shows goalkeepers form a perfectly isolated cluster, "
    "and outfield players separate into rich, overlapping "
    "sub-clusters by position and playing style - visual "
    "confirmation that the embedding space has real structure, "
    "even before any probing or SAE analysis."
)
st.caption(
    "Generate `umap_position.png` and `umap_rating.png` from "
    "notebook 04 and display them here with `st.image()` once "
    "available locally."
)
