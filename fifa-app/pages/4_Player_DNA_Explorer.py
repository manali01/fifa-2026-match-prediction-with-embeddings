"""
Player DNA Explorer - search any FIFA 22 player, see which of
the 87 SAE concepts activate for them, and compare two players
side by side.

Requires:
  outputs/models/sae_model.pt (or equivalent saved SAE weights)
  data/processed/players_22_processed.csv
  data/processed/player_embeddings.npy
  outputs/reports/sae_dimension_concepts.csv (dim -> concept name)
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title="Player DNA Explorer", page_icon="",
                    layout="wide")

import os
_SECRET = None
try:
    _SECRET = st.secrets.get("PROJECT_ROOT", None)
except Exception:
    pass
ROOT = Path(_SECRET) if _SECRET else Path(r"C:\Users\manal\fifa-embedding-risk")
DATA_PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "outputs" / "reports"

st.title(" Player DNA Explorer")
st.caption(
    "A Sparse Autoencoder trained on 23,803 player embeddings "
    "surfaced 87 monosemantic football concepts out of 512 "
    "dimensions - concepts the model discovered on its own, "
    "without ever being told what a 'center-back' is."
)


@st.cache_data
def load_player_data():
    players = pd.read_csv(DATA_PROC / "players_22_processed.csv")
    embeddings = np.load(DATA_PROC / "player_embeddings.npy")
    return players, embeddings


@st.cache_data
def load_sae_concepts():
    path = REPORTS / "sae_dimension_concepts.csv"
    if path.exists():
        return pd.read_csv(path)
    return None


try:
    players, embeddings = load_player_data()
except FileNotFoundError as e:
    st.error(
        f"Couldn't find player data: `{e.filename}`. Update "
        "`PROJECT_ROOT` in `.streamlit/secrets.toml`."
    )
    st.stop()

concepts_df = load_sae_concepts()

tab1, tab2 = st.tabs(["🔍 Search a Player", "⚖️ Compare Two Players"])

with tab1:
    name_query = st.text_input(
        "Search by player name",
        placeholder="e.g. Messi, Haaland, Mbappe",
    )

    if name_query:
        matches = players[
            players["short_name"].str.contains(
                name_query, case=False, na=False)
        ]
        if len(matches) == 0:
            st.warning("No players found matching that name.")
        else:
            selected = st.selectbox(
                "Select player",
                matches["short_name"].tolist(),
            )
            row = matches[matches["short_name"] == selected].iloc[0]

            c1, c2, c3 = st.columns(3)
            c1.metric("Overall", int(row["overall"]))
            c2.metric("Position", row["player_positions"])
            c3.metric("Nationality", row["nationality_name"])

            stat_cols = st.columns(6)
            for col, stat in zip(
                stat_cols,
                ["pace", "shooting", "passing", "dribbling",
                 "defending", "physic"],
            ):
                if stat in row and pd.notna(row[stat]):
                    col.metric(stat.capitalize(), int(row[stat]))

            if concepts_df is not None:
                st.divider()
                st.subheader("Top activating SAE concepts")
                st.caption(
                    "Which of the 87 discovered football concepts "
                    "fire most strongly for this player."
                )
                # Placeholder - wire up to your actual SAE
                # activation lookup once sae_model.pt is loaded
                st.info(
                    "Connect this section to your saved SAE model "
                    "(`outputs/models/sae_model.pt`) to show live "
                    "per-player activations. See notebook 10 for "
                    "the activation extraction code."
                )
            else:
                st.info(
                    "Run notebook 10 (SAE interpretability) and "
                    "export `sae_dimension_concepts.csv` to enable "
                    "concept lookups here."
                )

with tab2:
    st.write("Pick two players to compare their embedding "
            "similarity and stat profiles side by side.")

    pc1, pc2 = st.columns(2)
    with pc1:
        p1 = st.selectbox("Player 1",
                          players["short_name"].tolist(),
                          index=0, key="p1")
    with pc2:
        p2 = st.selectbox("Player 2",
                          players["short_name"].tolist(),
                          index=1, key="p2")

    if st.button("Compare", type="primary"):
        idx1 = players[players["short_name"] == p1].index[0]
        idx2 = players[players["short_name"] == p2].index[0]

        from sklearn.metrics.pairwise import cosine_similarity
        sim = cosine_similarity(
            embeddings[idx1].reshape(1, -1),
            embeddings[idx2].reshape(1, -1),
        )[0][0]

        st.metric("Embedding cosine similarity", f"{sim:.4f}")

        comp_df = pd.DataFrame({
            "Stat": ["Overall", "Pace", "Shooting", "Passing",
                    "Dribbling", "Defending", "Physic"],
            p1: [players.loc[idx1, c] for c in
                ["overall", "pace", "shooting", "passing",
                 "dribbling", "defending", "physic"]],
            p2: [players.loc[idx2, c] for c in
                ["overall", "pace", "shooting", "passing",
                 "dribbling", "defending", "physic"]],
        })
        st.dataframe(comp_df, use_container_width=True, hide_index=True)
        st.bar_chart(comp_df.set_index("Stat"))

st.divider()
st.caption(
    "Embeddings: sentence-transformers (all-MiniLM-L6-v2) over "
    "structured player text. SAE: 384 → 512 dims, λ=0.05 sparsity, "
    "89.5% of activations exactly zero, ~54 active concepts per "
    "player."
)
