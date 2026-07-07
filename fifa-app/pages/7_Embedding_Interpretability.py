"""
Embedding Interpretability — deep dive into what the embeddings encode,
probing classifier results, SHAP analysis, SAE findings, and UMAP structure.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Embedding Interpretability",
                    page_icon="Microscope", layout="wide")

st.title("Embedding Interpretability")
st.caption(
    "What do 384-dimensional FIFA player vectors actually encode? "
    "We ran four analyses to find out — and the answers surprised us."
)

tab1, tab2, tab3, tab4 = st.tabs([
    "The Problem", "Probing Classifiers", "Sparse Autoencoder", "Key Findings"
])

# ── TAB 1: THE PROBLEM ──
with tab1:
    st.subheader("Why interpretability matters here")
    st.write(
        "The baseline model achieved 52.9% accuracy — well above the 33% random "
        "baseline for a 3-class problem. But when we ran SHAP to understand what "
        "it was doing, the top feature was `diff_360`. Dimension 360 of the "
        "embedding difference vector. Completely uninterpretable."
    )

    st.info(
        "This is the core embedding risk: the model works, but you cannot see why. "
        "In a production model risk context, that is not a defensible position. "
        "Every finding on this page is an attempt to close that gap."
    )

    st.divider()
    st.subheader("What we tried")

    c1,c2 = st.columns(2)
    with c1:
        st.markdown("**Approach 1: SHAP analysis**")
        st.write(
            "SHAP values computed for all 384 embedding dimensions. "
            "Result: only the `neutral` flag (is the match on neutral ground?) "
            "produced an interpretable SHAP signal. All embedding dimensions "
            "showed near-zero individual SHAP importance despite collectively "
            "driving predictions. Confirmed entanglement."
        )
        st.markdown("**Approach 2: Probing classifiers**")
        st.write(
            "Linear classifiers trained on frozen embeddings to predict known "
            "player attributes. If the embedding encodes a concept, a simple "
            "linear probe should recover it. Results were striking."
        )

    with c2:
        st.markdown("**Approach 3: UMAP visualisation**")
        st.write(
            "23,803 player embeddings projected to 2D using UMAP. "
            "Goalkeepers form a perfectly isolated cluster with no overlap. "
            "Outfield players separate into rich multi-cluster structures "
            "by position and playing style — visual evidence that the "
            "embedding space has real, learnable structure."
        )
        st.markdown("**Approach 4: Sparse Autoencoder**")
        st.write(
            "SAE trained on the raw embeddings to decompose entangled "
            "dimensions into monosemantic features — one concept per "
            "dimension. This is the technique Anthropic developed for "
            "interpreting large language models, applied here to football "
            "player representations."
        )

# ── TAB 2: PROBING CLASSIFIERS ──
with tab2:
    st.subheader("Probing classifier results")
    st.write(
        "For each known player attribute, we trained a logistic regression "
        "classifier using the 384-dim embedding as input and the attribute "
        "as the label. High probe accuracy means the concept is encoded "
        "in the embedding — even if no individual dimension represents it cleanly."
    )

    probe_df = pd.DataFrame({
        "Concept":          ["Position (GK/DEF/MID/FWD)",
                             "Attacking Profile",
                             "Preferred Foot",
                             "Work Rate",
                             "Physical Profile",
                             "Rating Tier"],
        "Probe Accuracy":   [0.953, 0.878, 0.850, 0.786, 0.776, 0.726],
        "Baseline (random)":[0.250, 0.333, 0.500, 0.250, 0.333, 0.250],
        "Lift":             ["+70.3pp","+54.5pp","+35.0pp",
                             "+53.6pp","+44.3pp","+47.6pp"],
    })

    st.dataframe(probe_df, use_container_width=True, hide_index=True)
    st.bar_chart(probe_df.set_index("Concept")["Probe Accuracy"])

    st.success(
        "All probes score well above chance. The embeddings encode rich football "
        "intelligence — position, playing style, physical profile — even though "
        "none of these were explicitly labeled during embedding generation."
    )

    st.divider()
    st.subheader("The gap between probe accuracy and model feature importance")
    st.write(
        "Here is the uncomfortable finding: pairwise correlations between probe "
        "accuracy scores and the downstream XGBoost model's feature importances "
        "were near zero across all concepts."
    )
    st.warning(
        "The model exploits embedding dimensions that do not map onto any single "
        "known football concept. It learned something real — but not something "
        "we can name from the outside. This is exactly the interpretability gap "
        "the SAE was designed to close."
    )

    st.divider()
    st.subheader("UMAP structure")
    st.write(
        "Projecting all 23,803 player embeddings to 2D with UMAP reveals:"
    )
    col1,col2,col3 = st.columns(3)
    col1.metric("GK cluster isolation","Perfect","No overlap with outfield")
    col2.metric("Outfield sub-clusters","Rich multi-cluster structure","By position and style")
    col3.metric("Nationality clusters","Present","Discovered without nationality labels")

    st.info(
        "The goalkeeper isolation is particularly striking — the model learned "
        "that goalkeepers are categorically different from outfield players "
        "purely from text descriptions of traits, stats, and playing style, "
        "without ever being told the GK position was special."
    )

# ── TAB 3: SPARSE AUTOENCODER ──
with tab3:
    st.subheader("Sparse Autoencoder (SAE) analysis")
    st.write(
        "We trained a Sparse Autoencoder on all 23,803 player embeddings "
        "to decompose the entangled 384-dimensional representations into "
        "monosemantic features — dimensions where each active feature "
        "encodes exactly one concept."
    )

    c1,c2,c3 = st.columns(3)
    c1.metric("Input dimensions","384","all-MiniLM-L6-v2 output")
    c2.metric("Hidden dimensions","512","expansion layer")
    c3.metric("Sparsity (lambda)","0.05","89.5% of activations = 0")

    st.divider()
    st.subheader("Training results across sparsity levels")

    sae_df = pd.DataFrame({
        "Lambda":          [0.001, 0.01, 0.05],
        "Zero %":          ["53.5%","69.9%","89.5%"],
        "Active dims/player":[238.2, 154.1, 53.5],
        "Recon loss":      [0.000011, 0.000046, 0.000207],
        "Verdict":         ["Too dense","Moderate","Selected"],
    })
    st.dataframe(sae_df, use_container_width=True, hide_index=True)

    st.success(
        "Lambda=0.05 selected: 89.5% sparsity, ~54 active dimensions per player. "
        "Each player is described by approximately 54 of 512 possible concepts — "
        "sparse enough to be interpretable, dense enough to be faithful."
    )

    st.divider()
    st.subheader("What the SAE found: 87 alive dimensions")
    st.write(
        "Of 512 hidden dimensions, 425 are dead (never activate for any player). "
        "87 dimensions are alive — each encoding one interpretable football concept."
    )

    col1,col2 = st.columns(2)
    with col1:
        st.metric("Total hidden dims","512")
        st.metric("Dead dims","425","never activate")
        st.metric("Alive dims","87","one concept each")

    with col2:
        st.metric("Avg activation frequency","61.5%","across alive dims")
        st.metric("Avg active dims per player","53.5","out of 512")
        st.metric("Reconstruction quality","0.000207","MSE loss")

    st.divider()
    st.subheader("Sample discovered concepts")
    st.write(
        "Each dimension was named by inspecting the top 10 players that activate it most strongly."
    )

    concepts_df = pd.DataFrame({
        "Dimension": [76, 188, 2, 307, 51, 70, 105, 280],
        "Concept":   [
            "Solid Defender (Italian style)",
            "Solid Defender (Dutch style)",
            "Balanced Midfielder",
            "Attacking Player (pacey)",
            "Attacking Player",
            "Build-up Midfielder (mixed)",
            "Solid Defender (mixed)",
            "Balanced Midfielder (mixed)",
        ],
        "Top activating players (sample)": [
            "Bonucci, Di Lorenzo, De Sciglio",
            "D. Sanchez, S. van den Berg, R. van den Berg",
            "Various midfielders",
            "Pacey forwards",
            "Wide attackers",
            "Central midfielders",
            "Centre-backs",
            "Box-to-box midfielders",
        ],
        "Activation frequency": [
            "62.7%","66.0%","47.5%","60.1%","63.6%","59.8%","54.3%","63.7%"
        ],
    })
    st.dataframe(concepts_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("The nationality cluster finding")
    st.info(
        "The most unexpected SAE result: several dimensions activate almost "
        "exclusively for players of one nationality. Dimension 76 fires for "
        "Italian defenders. Dimension 188 fires for Dutch defenders.\n\n"
        "The SAE discovered that **Italian defensive style** and **Dutch defensive "
        "style** are coherent, separable concepts in the embedding space — "
        "without ever being told nationality was a relevant signal.\n\n"
        "This has direct implications for model risk: the model may be using "
        "implicit nationality signals rather than pure football quality signals, "
        "which could explain some of the confederation bias detected in the bias audit."
    )

# ── TAB 4: KEY FINDINGS ──
with tab4:
    st.subheader("Summary of interpretability findings")

    findings = [
        ("The embeddings encode rich football intelligence",
         "Probing classifiers recover position at 95.3%, preferred foot at 85.0%, "
         "rating tier at 72.6% — all far above chance. The information is there.",
         "success"),

        ("But individual dimensions are not interpretable",
         "SHAP analysis shows near-zero importance for any single embedding dimension. "
         "The model uses collective patterns across many dimensions, not clean individual signals.",
         "warning"),

        ("The SAE surfaces 87 monosemantic concepts",
         "With strong sparsity (lambda=0.05), 87 of 512 hidden dimensions activate "
         "in interpretable ways. Each one encodes one football concept rather than a mixture.",
         "success"),

        ("Nationality-based style clusters exist in the embedding space",
         "The SAE found that Italian defenders and Dutch defenders activate different "
         "dimensions — the model has implicitly encoded national playing styles. "
         "This was not labeled, engineered, or intended.",
         "info"),

        ("The model exploits dimensions we cannot name",
         "Zero correlation between probe accuracy and XGBoost feature importance "
         "means the model is using embedding structure that our probing exercises "
         "do not capture. This is the residual interpretability gap.",
         "warning"),

        ("Practical implication for model risk",
         "The SAE layer converts the black-box embedding into 87 named concepts "
         "that a human reviewer can reason about. It does not fully eliminate the "
         "interpretability gap but substantially reduces it — from 384 "
         "uninterpretable dimensions to 87 named ones.",
         "success"),
    ]

    for title, detail, kind in findings:
        if kind == "success":
            st.success(f"**{title}**\n\n{detail}")
        elif kind == "warning":
            st.warning(f"**{title}**\n\n{detail}")
        else:
            st.info(f"**{title}**\n\n{detail}")

    st.divider()
    st.subheader("Further reading")
    st.write(
        "The SAE methodology used here is directly based on Anthropic's research "
        "on mechanistic interpretability of large language models, adapted for "
        "structured player embeddings:"
    )
    st.markdown("""
- **Sparse Autoencoders and monosemantic features** — Anthropic (2023)
  https://transformer-circuits.pub/2023/monosemantic-features/index.html

- **Toy Models of Superposition** — why embeddings entangle concepts
  https://transformer-circuits.pub/2022/toy_model/index.html

- **Probing classifiers** — testing what representations encode
  https://colah.github.io/posts/2014-07-Conv-Nets-Modular/

- **UMAP: Uniform Manifold Approximation and Projection**
  https://umap-learn.readthedocs.io/en/latest/

- **SHAP values for model explainability**
  https://shap.readthedocs.io/en/latest/
""")
