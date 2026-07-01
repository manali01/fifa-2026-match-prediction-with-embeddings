"""
Match Predictor page - pick any two national teams, get a live
V5 prediction with full feature breakdown.

Expects these artifacts to exist on disk (adjust paths in
config.py to match your local project layout):

  outputs/models/clf_v5.pkl
  outputs/models/label_encoder.pkl
  outputs/models/pca_model.pkl
  data/processed/wc2026_team_embeddings.csv
  data/processed/players_22_processed.csv
  data/processed/player_embeddings_enriched.npy
  data/raw/fifa_ranking-2024-06-20.csv
  data/raw/results.csv
"""
import streamlit as st
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="Match Predictor", page_icon="",
                    layout="wide")

# ── Project root - hardcoded for local use ──
import os
_SECRET = None
try:
    _SECRET = st.secrets.get("PROJECT_ROOT", None)
except Exception:
    pass
ROOT = Path(_SECRET) if _SECRET else Path(r"C:\Users\manal\fifa-embedding-risk")
MODELS = ROOT / "outputs" / "models"
DATA_PROC = ROOT / "data" / "processed"
DATA_RAW = ROOT / "data" / "raw"


@st.cache_resource
def load_artifacts():
    with open(MODELS / "clf_v5.pkl", "rb") as f:
        clf_v5 = pickle.load(f)
    with open(MODELS / "label_encoder.pkl", "rb") as f:
        le = pickle.load(f)
    with open(MODELS / "pca_model.pkl", "rb") as f:
        pca_k = pickle.load(f)

    wc_team_emb_df = pd.read_csv(
        DATA_PROC / "wc2026_team_embeddings.csv")
    wc_team_indexed = wc_team_emb_df.set_index("nationality_name")
    emb_cols = [f"emb_{i}" for i in range(384)]

    rankings = pd.read_csv(
        DATA_RAW / "fifa_ranking-2024-06-20.csv",
        usecols=["country_full", "total_points", "rank_date"],
        parse_dates=["rank_date"],
    ).sort_values("rank_date").reset_index(drop=True)

    results_full = pd.read_csv(DATA_RAW / "results.csv",
                                parse_dates=["date"])
    results_competitive = results_full[
        ~results_full["tournament"].str.contains(
            "Friendly", case=False, na=False)
    ].copy()

    return (clf_v5, le, pca_k, wc_team_indexed, emb_cols,
            rankings, results_competitive)


WORLD_CUP_2026 = {
    'Argentina': 'Argentina', 'Brazil': 'Brazil', 'Colombia': 'Colombia',
    'Ecuador': 'Ecuador', 'Uruguay': 'Uruguay', 'Paraguay': 'Paraguay',
    'France': 'France', 'England': 'England', 'Spain': 'Spain',
    'Germany': 'Germany', 'Portugal': 'Portugal',
    'Netherlands': 'Netherlands', 'Belgium': 'Belgium',
    'Croatia': 'Croatia', 'Switzerland': 'Switzerland',
    'Austria': 'Austria', 'Denmark': 'Denmark', 'Albania': 'Albania',
    'Turkey': 'Turkey', 'Ukraine': 'Ukraine', 'Sweden': 'Sweden',
    'Bosnia and Herzegovina': 'Bosnia and Herzegovina',
    'Czechia': 'Czech Republic', 'Georgia': 'Georgia',
    'Scotland': 'Scotland', 'Slovenia': 'Slovenia',
    'Slovakia': 'Slovakia', 'Hungary': 'Hungary',
    'United States': 'United States', 'Mexico': 'Mexico',
    'Canada': 'Canada', 'Panama': 'Panama', 'Honduras': 'Honduras',
    'Curacao': 'Curacao', 'Japan': 'Japan',
    'South Korea': 'Korea Republic', 'Iran': 'Iran',
    'Australia': 'Australia', 'Saudi Arabia': 'Saudi Arabia',
    'Uzbekistan': 'Uzbekistan', 'Qatar': 'Qatar', 'Jordan': 'Jordan',
    'Iraq': 'Iraq', 'Morocco': 'Morocco', 'Senegal': 'Senegal',
    'Egypt': 'Egypt', 'Algeria': 'Algeria',
    'Ivory Coast': "Côte d'Ivoire", 'South Africa': 'South Africa',
    'Mali': 'Mali', 'Tunisia': 'Tunisia',
    'Cape Verde': 'Cape Verde Islands', 'DR Congo': 'Congo DR',
    'New Zealand': 'New Zealand', 'Haiti': 'Haiti',
    'Norway': 'Norway', 'Ghana': 'Ghana',
}

RANKING_NAME_MAP = {
    'United States': 'USA', 'South Korea': 'Korea Republic',
    'Ivory Coast': "Côte d'Ivoire", 'Czechia': 'Czech Republic',
    'Cape Verde': 'Cabo Verde', 'Iran': 'IR Iran', 'Turkey': 'Türkiye',
}


def get_ranking_points(team, date, rankings_df):
    name = RANKING_NAME_MAP.get(team, team)
    for n in (name, team):
        tr = rankings_df[rankings_df["country_full"] == n]
        if len(tr) > 0:
            past = tr[tr["rank_date"] <= date]
            return (past.iloc[-1]["total_points"] if len(past) > 0
                    else tr.iloc[0]["total_points"])
    return 1000


def get_h2h_stats(home, away, date, rc, n=10):
    h2h = rc[
        ((rc["home_team"] == home) & (rc["away_team"] == away)) |
        ((rc["home_team"] == away) & (rc["away_team"] == home))
    ]
    h2h = h2h[h2h["date"] < date].sort_values(
        "date", ascending=False).head(n)
    if len(h2h) == 0:
        return {"h2h_home_wr": 0.33, "h2h_draw_rate": 0.33,
                "h2h_last": 0, "h2h_n": 0}
    hw = dr = aw = 0
    for _, r in h2h.iterrows():
        hs, as_ = r["home_score"], r["away_score"]
        if pd.isna(hs) or pd.isna(as_):
            continue
        if r["home_team"] == home:
            hw += hs > as_; dr += hs == as_; aw += hs < as_
        else:
            hw += as_ > hs; dr += hs == as_; aw += as_ < hs
    tot = hw + dr + aw
    if tot == 0:
        return {"h2h_home_wr": 0.33, "h2h_draw_rate": 0.33,
                "h2h_last": 0, "h2h_n": 0}
    last = h2h.iloc[0]
    if last["home_team"] == home:
        hl = (1 if last["home_score"] > last["away_score"] else
              0 if last["home_score"] == last["away_score"] else -1)
    else:
        hl = (1 if last["away_score"] > last["home_score"] else
              0 if last["home_score"] == last["away_score"] else -1)
    return {"h2h_home_wr": round(hw/tot, 3),
            "h2h_draw_rate": round(dr/tot, 3),
            "h2h_last": hl, "h2h_n": tot}


def get_competitive_form(team, date, rc, n=5):
    tm = rc[(rc["home_team"] == team) | (rc["away_team"] == team)]
    tm = tm[tm["date"] < date].sort_values(
        "date", ascending=False).head(n)
    if len(tm) == 0:
        return {"comp_pts": 0, "comp_gd": 0, "comp_streak": 0}
    pts = gf = ga = streak = 0
    streak_active = True
    for _, r in tm.iterrows():
        hs, as_ = r["home_score"], r["away_score"]
        if pd.isna(hs) or pd.isna(as_):
            continue
        if r["home_team"] == team:
            tgf, tga = hs, as_
        else:
            tgf, tga = as_, hs
        if tgf > tga:
            pts += 3
            if streak_active:
                streak += 1
        elif tgf == tga:
            pts += 1
            streak_active = False
        else:
            if streak_active:
                streak -= 1
            streak_active = False
        gf += tgf; ga += tga
    return {"comp_pts": pts, "comp_gd": gf-ga, "comp_streak": streak}


def predict_match(home, away, neutral, match_date,
                   clf_v5, le, pca_k, wc_team_indexed, emb_cols,
                   rankings, results_competitive):
    hf = WORLD_CUP_2026.get(home, home)
    af = WORLD_CUP_2026.get(away, away)
    if hf not in wc_team_indexed.index or af not in wc_team_indexed.index:
        return None

    he = wc_team_indexed.loc[hf, emb_cols].values
    ae = wc_team_indexed.loc[af, emb_cols].values
    dp = pca_k.transform((he - ae).reshape(1, -1))[0]
    es = cosine_similarity(he.reshape(1, -1), ae.reshape(1, -1))[0][0]

    hp = get_ranking_points(home, match_date, rankings)
    ap = get_ranking_points(away, match_date, rankings)
    h2h = get_h2h_stats(home, away, match_date, results_competitive)
    hc = get_competitive_form(home, match_date, results_competitive)
    ac = get_competitive_form(away, match_date, results_competitive)

    fv = np.array([
        int(neutral), hp - ap, hp, ap, 3,
        h2h["h2h_home_wr"], h2h["h2h_draw_rate"], h2h["h2h_last"],
        hc["comp_pts"] - ac["comp_pts"],
        hc["comp_gd"] - ac["comp_gd"],
        hc["comp_streak"] - ac["comp_streak"],
        es, *dp,
    ]).reshape(1, -1)

    probs = clf_v5.predict_proba(fv)[0]
    pred_label = le.inverse_transform([np.argmax(probs)])[0]
    winner = (home if pred_label == "Home Win" else
              away if pred_label == "Away Win" else "Draw")

    return {
        "winner": winner,
        "prob_home_win": float(probs[2]),
        "prob_draw": float(probs[1]),
        "prob_away_win": float(probs[0]),
        "emb_sim": float(es),
        "ranking_diff": float(hp - ap),
        "h2h": h2h,
        "home_comp": hc,
        "away_comp": ac,
    }


# ── UI ──
st.title(" Match Predictor")
st.caption("V5 model - embeddings, rankings, H2H history and "
           "competitive form, trained end-to-end on 10,434 "
           "international matches (2010-2023).")

try:
    (clf_v5, le, pca_k, wc_team_indexed, emb_cols,
     rankings, results_competitive) = load_artifacts()
except FileNotFoundError as e:
    st.error(
        f"Couldn't find model artifacts: `{e.filename}`.\n\n"
        "Update `PROJECT_ROOT` in `.streamlit/secrets.toml` to "
        "point at your `fifa-embedding-risk` project folder."
    )
    st.stop()

teams = sorted(WORLD_CUP_2026.keys())

# ── Match type ──
match_type = st.radio(
    "Match type",
    ["Group Stage (draw possible)", "Knockout (no draw - ET/pens decide)"],
    horizontal=True,
)
is_knockout = "Knockout" in match_type

if is_knockout:
    st.info(
        "Knockout mode: draw probability is redistributed "
        "proportionally to each team's win probability, "
        "reflecting that someone must advance after extra time "
        "and penalties."
    )

col1, col2, col3 = st.columns([2, 1, 2])
with col1:
    home_team = st.selectbox("Home team", teams,
                              index=teams.index("Argentina"))
with col2:
    st.markdown("<h2 style='text-align:center; margin-top:1.7rem;'>"
                "vs</h2>", unsafe_allow_html=True)
    # Knockout matches are always neutral; group matches let user choose
    neutral = True if is_knockout else st.checkbox(
        "Neutral venue", value=True)
with col3:
    away_default = "Brazil" if "Brazil" in teams else teams[1]
    away_team = st.selectbox("Away team", teams,
                              index=teams.index(away_default))

predict_clicked = st.button("Predict Match", type="primary",
                             use_container_width=True)

if predict_clicked:
    if home_team == away_team:
        st.warning("Pick two different teams.")
        st.stop()

    match_date = pd.Timestamp("2026-06-18")
    result = predict_match(
        home_team, away_team, neutral, match_date,
        clf_v5, le, pca_k, wc_team_indexed, emb_cols,
        rankings, results_competitive,
    )

    if result is None:
        st.error(f"One of {home_team}/{away_team} isn't in the "
                 "WC 2026 team embeddings yet. Run the fix cell "
                 "in notebook 09 and re-save wc2026_team_embeddings.csv.")
        st.stop()

    # ── Knockout: redistribute draw prob ──
    if is_knockout:
        hw = result["prob_home_win"]
        aw = result["prob_away_win"]
        dr = result["prob_draw"]
        # Split draw proportionally: team with higher base prob
        # gets proportionally more of the draw redistribution
        total_non_draw = hw + aw
        adj_hw = hw + dr * (hw / total_non_draw)
        adj_aw = aw + dr * (aw / total_non_draw)
        result["prob_home_win"] = adj_hw
        result["prob_away_win"] = adj_aw
        result["prob_draw"] = 0.0
        result["winner"] = home_team if adj_hw > adj_aw else away_team

    st.divider()
    st.subheader(f"{home_team}  vs  {away_team}")

    if is_knockout:
        # Two-column layout - no draw column
        pc1, pc2 = st.columns(2)
        with pc1:
            st.metric(
                f"🏠 {home_team} advances",
                f"{result['prob_home_win']:.1%}",
                help="Probability of winning in 90 min, ET, or penalties"
            )
        with pc2:
            st.metric(
                f"✈️ {away_team} advances",
                f"{result['prob_away_win']:.1%}",
                help="Probability of winning in 90 min, ET, or penalties"
            )
        st.caption(
            "Probabilities reflect who is more likely to advance - "
            "not necessarily to win in 90 minutes. The base model "
            "assigns some probability to a draw outcome; in knockout "
            "mode that is redistributed proportionally, since "
            "penalties will always produce a winner."
        )
    else:
        # Three-column layout - draw shown
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            st.metric(f" {home_team} Win",
                      f"{result['prob_home_win']:.1%}")
        with pc2:
            st.metric(" Draw", f"{result['prob_draw']:.1%}")
        with pc3:
            st.metric(f"️ {away_team} Win",
                      f"{result['prob_away_win']:.1%}")
        st.caption(
            "Model validated OOT at 71.0% on the 2026 WC group "
            "stage (Home Win 77%, Away Win 100%, Draw 33%). "
            "Draws are the hardest class - see Embedding Risk "
            "Dashboard for full breakdown."
        )

    winner_label = ("🏆 Advances: " if is_knockout else "🏆 Predicted winner: ")
    st.progress(
        result["prob_home_win"],
        text=f"{winner_label}**{result['winner']}** "
             f"({result['prob_home_win']:.1%} vs "
             f"{result['prob_away_win']:.1%})"
    )

    st.divider()
    st.subheader("What drove this prediction")

    fc1, fc2 = st.columns(2)
    with fc1:
        st.markdown("**Head-to-head history (competitive only)**")
        h2h = result["h2h"]
        if h2h["h2h_n"] > 0:
            st.write(f"- {h2h['h2h_n']} prior competitive meetings")
            st.write(f"- {home_team} win rate: {h2h['h2h_home_wr']:.0%}")
            if not is_knockout:
                st.write(f"- Historical draw rate: {h2h['h2h_draw_rate']:.0%}")
            last_map = {1: f"{home_team} won", 0: "Draw",
                        -1: f"{away_team} won"}
            st.write(f"- Last meeting: {last_map[h2h['h2h_last']]}")
        else:
            st.write("- No prior competitive meetings on record")

    with fc2:
        st.markdown("**Recent competitive form (last 5)**")
        hc, ac = result["home_comp"], result["away_comp"]
        st.write(f"- {home_team}: {int(hc['comp_pts'])} pts, "
                 f"GD {int(hc['comp_gd']):+d}, "
                 f"streak {int(hc['comp_streak']):+d}")
        st.write(f"- {away_team}: {int(ac['comp_pts'])} pts, "
                 f"GD {int(ac['comp_gd']):+d}, "
                 f"streak {int(ac['comp_streak']):+d}")

    st.markdown("**Squad similarity & ranking gap**")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.write(f"Embedding cosine similarity: "
                 f"`{result['emb_sim']:.4f}`")
        if result["emb_sim"] > 0.995 and not is_knockout:
            st.caption("️ Very similar squads - draw risk elevated "
                       "in group stage")
    with sc2:
        st.write(f"FIFA ranking points gap: "
                 f"`{result['ranking_diff']:+.1f}`")
