# FIFA Embedding Risk — Streamlit App

A football match prediction system: built, questioned, and
stress-tested before going live on the 2026 World Cup.

## Pages

| Page | What it does |
|---|---|
| **Home** | Project story — the 5-act narrative |
| **⚽ Match Predictor** | Pick any two teams, get a live V5 prediction with full feature breakdown |
| **🛡️ Embedding Risk Dashboard** | Temporal validation, OOD detection, bias audit, stability tests, SR 26-2 model card |
| **🏆 WC 2026 Bracket** | Round of 32 → Final predictions, updated as results come in |
| **🧬 Player DNA Explorer** | Search any player, explore SAE concept activations, compare two players |
| **🔬 How It Works** | Pipeline walkthrough, probing classifier results, SAE concept gallery |

## Setup

```bash
cd fifa-app
pip install -r requirements.txt

# Point the app at your local project data/models
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml — set PROJECT_ROOT to your
# fifa-embedding-risk folder (the one containing data/ and outputs/)

streamlit run Home.py
```

## Expected file layout at PROJECT_ROOT

```
PROJECT_ROOT/
├── data/
│   ├── raw/
│   │   ├── fifa_ranking-2024-06-20.csv
│   │   └── results.csv
│   └── processed/
│       ├── players_22_processed.csv
│       ├── player_embeddings.npy
│       └── wc2026_team_embeddings.csv
└── outputs/
    ├── models/
    │   ├── clf_v5.pkl
    │   ├── label_encoder.pkl
    │   └── pca_model.pkl
    └── reports/
        ├── wc2026_v5_final_predictions.csv
        └── sae_dimension_concepts.csv   (optional — see notebook 10)
```

## Deploying

**Streamlit Community Cloud** (free, easiest):
1. Push this `fifa-app/` folder (plus the data/models it needs,
   or a script that downloads them) to a public GitHub repo
2. Connect the repo at share.streamlit.io
3. Add `PROJECT_ROOT` in the app's Secrets settings, pointing
   at wherever you've bundled the data inside the repo
4. Deploy

Note: model `.pkl` files and the player embeddings `.npy` are
likely too large for a free-tier GitHub repo as-is — consider
Git LFS, or re-deriving a lightweight subset of the data
specifically for the demo app.
