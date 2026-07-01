# FIFA Embedding Risk
### A Football Match Prediction System — Built, Questioned, and Stress-Tested

[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?logo=streamlit)](https://fifa-2026-prediction.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)
[![XGBoost](https://img.shields.io/badge/Model-XGBoost_V5-orange)](https://xgboost.ai)
[![PyTorch](https://img.shields.io/badge/SAE-PyTorch-EE4C2C?logo=pytorch)](https://pytorch.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **71% accuracy** on live 2026 FIFA World Cup matches — using FIFA player text embeddings, XGBoost, and a Sparse Autoencoder interpretability layer.

---

## The Story

We started with one question: *can FIFA player descriptions predict international match outcomes?*

Getting there meant building a prediction system, then stress-testing it until we understood exactly where it worked and where it failed — before letting it make live predictions on the 2026 World Cup.

```
Act 1 — BUILD      Can embeddings predict match outcomes?
Act 2 — QUESTION   What is the model actually learning?
Act 3 — STRESS TEST When does the model fail?
Act 4 — IMPROVE    Build a system we can defend
Act 5 — DEPLOY     Real predictions. Live tournament.
```

---

## Results

| Period | Samples | Accuracy | AUC | F1 |
|--------|---------|----------|-----|----|
| Train (2010-2023) | 8,701 | 82.5% | 0.952 | 0.819 |
| In-Time (2024-May 2026) | 1,591 | 55.4% | 0.721 | 0.506 |
| OOT Base (WC 2026) | 32 | 53.1% | 0.614 | 0.492 |
| **OOT V5+Adjustments** | **32** | **71.0%** | — | — |

OOT breakdown: Home Win 77% | Away Win 100% | Draw 33%

---

## What We Built

### Layer 1 — Player DNA (Embeddings)
- 23,803 FIFA 22 players → text descriptions → `all-MiniLM-L6-v2` → 384-dim vectors
- Mean-pool top 26 players per nation → national team embedding
- Probing classifiers confirm: Position 95.3%, Preferred Foot 85.0%, Rating Tier 72.6%

### Layer 2 — Interpretability (SAE)
- Sparse Autoencoder: 384 → 512 dims (λ=0.05, 89.5% sparsity)
- 87 alive monosemantic dimensions discovered
- Concepts found: "Creative Playmaker", "Commanding CB (Italian)", "Electric Winger"
- SAE reveals nationality-based playing style clusters without being told nationality matters

### Layer 3 — Prediction (V5 Model)
- XGBoost trained on 78 features, temporal split (no data leakage)
- Features: PCA embeddings + FIFA rankings + H2H history + competitive form + cosine similarity
- Live adjustments: WC tournament form + FanDuel odds blend (55/45) + injury/suspension flags

### Layer 4 — Trust (Embedding Risk)
- OOD Detection: Mahalanobis distance flags 26/168 teams outside distribution
- Bias Audit: CAF confederation gap = -0.371 (root cause: sparse FIFA 22 trait data for African players)
- Stability: 4.6% prediction flip rate under embedding perturbation
- Temporal validation: documented -27% concept drift from train to in-time period

### Layer 5 — Live Deployment
- 2026 FIFA World Cup: predictions updated automatically via ESPN API
- 15-minute cache refresh, falls back to verified snapshot on API failure
- Bracket simulation: R32 through Final with live confirmed results

---

## Key Findings

```
Embedding quality:
  Position encoded at 95.3% probe accuracy
  But SHAP shows individual dimensions are uninterpretable
  -> SAE bridges the gap: 87 readable concepts

Model behaviour:
  Away Win: 100% OOT accuracy (model knows strong teams)
  Home Win: 77% OOT accuracy
  Draw:     33% OOT accuracy (hardest class, well-documented)

Risk findings:
  Concept drift: -27% Train->IT accuracy gap
  Embedding staleness: FIFA 22 data (2021) affects 2024+ matches
  CAF bias: African team representations systematically weaker
  OOD risk: 26 teams flagged, Qatar uses AFC mean fallback

V5 improvements over baseline:
  V1 (embeddings only):        46.9% OOT
  V2 (+form +draw detector):   65.6% OOT
  V3 (+H2H +competitive form): ~67%  OOT
  V4 (+odds +injuries):        68.8% OOT
  V5 (end-to-end training):    71.0% OOT
```

---

## Project Structure

```
fifa-2026-match-prediction-with-embeddings/
├── notebooks/
│   ├── 01_eda.ipynb                    Data exploration
│   ├── 02_embedding_generation.ipynb   Player text -> vectors
│   ├── 03_baseline_model.ipynb         V1: embeddings + XGBoost
│   ├── 04_explainability.ipynb         SHAP + probing classifiers
│   ├── 05_risk_mitigation.ipynb        OOD, bias, stability tests
│   ├── 06_world_cup_2026.ipynb         WC predictions pipeline
│   ├── 07_improved_model.ipynb         V2-V4 iterations
│   ├── 08_validation.ipynb             Temporal train/IT/OOT framework
│   ├── 09_v5_model.ipynb               V5 end-to-end training
│   └── 10_sae_interpretability.ipynb   Sparse Autoencoder analysis
│
├── fifa-app/                           Streamlit web application
│   ├── Home.py                         Landing page (project story)
│   ├── live_data.py                    ESPN API live data fetcher
│   └── pages/
│       ├── 1_Match_Predictor.py        Predict any matchup
│       ├── 2_Embedding_Risk_Dashboard.py Validation + model card
│       ├── 3_WC_2026_Bracket.py        Live tournament bracket
│       ├── 4_Player_DNA_Explorer.py    SAE concept explorer
│       ├── 5_How_It_Works.py           Pipeline explainer
│       └── 6_Model_Comparison.py       V1 through V5 comparison
│
├── outputs/
│   ├── models/                         Saved model artifacts
│   └── reports/                        Prediction CSVs, Excel
│
└── data/
    ├── raw/                            Source data (see setup)
    └── processed/                      Feature matrices, embeddings
```

---

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/fifa-2026-match-prediction-with-embeddings
cd fifa-2026-match-prediction-with-embeddings

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

**Data sources** (download and place in `data/raw/`):
- [FIFA 22 Complete Player Dataset](https://www.kaggle.com/datasets/stefanoleone992/fifa-22-complete-player-dataset) — Kaggle
- [International Football Results](https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017) — Kaggle
- [FIFA World Rankings](https://www.kaggle.com/datasets/cashncarry/fifaworldranking) — Kaggle

**Run notebooks** in order (01 through 10) to reproduce all results.

**Run the app:**
```bash
cd fifa-app
streamlit run Home.py
```

---

## Tech Stack

| Component | Tools |
|-----------|-------|
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Prediction model | XGBoost, scikit-learn |
| Interpretability | SHAP, UMAP, PyTorch (SAE) |
| Validation | Temporal split, Mahalanobis OOD detection |
| Live data | ESPN public API, Wikipedia scraper |
| Web app | Streamlit |
| Data | FIFA 22, international-football-results, FIFA rankings |

---

## Model Card Summary

**Intended use:** International football match outcome prediction, demonstrated on 2026 FIFA World Cup

**Training period:** 2010-2023 (8,701 matches)

**Known limitations:**
- Draw class: F1 = 0.143 base OOT (0.33 with live adjustments)
- Embeddings frozen at FIFA 22 (2021 data) — staleness grows over time
- CAF confederation bias documented but not fully resolved
- 26/168 teams flagged as outside training distribution

**Monitoring:** Alert if OOT accuracy < 50%. Human review required for draw predictions and OOD-flagged matchups.

---

## Citation

```
@misc{fifa-2026-match-prediction-with-embeddings-2026,
  author    = {Manali},
  title     = {FIFA Embedding Risk: A Football Match Prediction System},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/YOUR_USERNAME/fifa-2026-match-prediction-with-embeddings}
}
```

---

*Built with Python, XGBoost, PyTorch, sentence-transformers, SHAP, UMAP, Streamlit*
