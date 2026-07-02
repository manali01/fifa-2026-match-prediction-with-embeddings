"""
WC 2026 Bracket — live data from ESPN API + verified snapshot.
Auto-refreshes every 15 minutes. Confirmed results shown as confirmed.
Predictions shown for upcoming matches.
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="WC 2026 Bracket", page_icon="Trophy",
                    layout="wide")

st.title("2026 FIFA World Cup - Live Tournament Bracket")

# ── Load live data ──
try:
    from live_data import get_live_data, model_accuracy_r32
    with st.spinner("Fetching latest results..."):
        data = get_live_data()

    c, t = model_accuracy_r32(data)
    col1,col2,col3,col4 = st.columns(4)
    col1.metric("R32 Completed", f"{data['r32_complete']}/16")
    col2.metric("Model Accuracy (R32)", f"{c}/{t} ({int(c/t*100) if t else 0}%)")
    col3.metric("Last Updated", data['last_updated'].split('(')[0].strip())
    col4.metric("Data Source", data['data_source'].split('+')[0].strip())

    confirmed_r32  = data.get("confirmed_r32_raw", {})
    r32_preds      = data["r32_predictions"]
    upsets         = data["upsets"]
    injuries       = data["injury_flags"]

    if upsets:
        msgs = " | ".join(
            f"{u['match']}: {u['result']}"
            for u in upsets
        )
        st.error(f"UPSETS: {msgs}")

except Exception as e:
    st.warning(f"Could not load live data module: {e}")
    confirmed_r32 = {}
    r32_preds     = {}
    upsets        = []
    injuries      = {}

st.divider()

# ── Group data (final standings) ──
group_data = {
    "A": [("Mexico",9,6,True),("South Africa",4,0,True),
          ("South Korea",3,0,False),("Czechia",1,-6,False)],
    "B": [("Switzerland",7,5,True),("Canada",5,5,True),
          ("Bosnia & Herz.",4,2,True),("Qatar",0,-12,False)],
    "C": [("Brazil",7,6,True),("Morocco",4,4,True),
          ("Scotland",3,0,False),("Haiti",0,-10,False)],
    "D": [("United States",6,3,True),("Paraguay",4,-1,True),
          ("Australia",1,-1,False),("Turkey",3,-1,False)],
    "E": [("Germany",6,5,True),("Ivory Coast",4,3,True),
          ("Ecuador",2,-2,False),("Curacao",0,-6,False)],
    "F": [("Netherlands",9,7,True),("Japan",4,1,True),
          ("Sweden",2,2,True),("Tunisia",0,-10,False)],
    "G": [("Belgium",6,5,True),("Egypt",4,1,True),
          ("New Zealand",1,-1,False),("Iran",0,-5,False)],
    "H": [("Spain",7,5,True),("Cape Verde",2,0,True),
          ("Uruguay",1,0,False),("Saudi Arabia",1,-5,False)],
    "I": [("France",7,6,True),("Norway",7,5,True),
          ("Senegal",3,0,False),("Iraq",0,-11,False)],
    "J": [("Argentina",9,7,True),("Austria",3,1,True),
          ("Algeria",3,0,True),("Jordan",0,-8,False)],
    "K": [("Colombia",5,3,True),("Portugal",3,2,True),
          ("DR Congo",2,0,False),("Uzbekistan",2,-5,False)],
    "L": [("England",9,7,True),("Croatia",6,2,True),
          ("Ghana",3,-1,True),("Panama",0,-8,False)],
}

# ── All R32 fixtures ──
r32_fixtures = [
    ("Jun 28","Canada","South Africa"),
    ("Jun 29","Brazil","Japan"),
    ("Jun 29","Germany","Paraguay"),
    ("Jun 29","Netherlands","Morocco"),
    ("Jun 30","Norway","Ivory Coast"),
    ("Jun 30","France","Sweden"),
    ("Jun 30","Mexico","Ecuador"),
    ("Jul 1","England","DR Congo"),
    ("Jul 1","Belgium","Senegal"),
    ("Jul 1","United States","Bosnia and Herzegovina"),
    ("Jul 2","Spain","Austria"),
    ("Jul 2","Portugal","Croatia"),
    ("Jul 2","Switzerland","Algeria"),
    ("Jul 3","Australia","Egypt"),
    ("Jul 3","Argentina","Cape Verde"),
    ("Jul 3","Colombia","Ghana"),
]

tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "Group Stage",
    "Round of 32",
    "Round of 16",
    "Quarters and Semis",
    "Final and Champion",
])

# ── GROUP STAGE ──
with tab1:
    st.subheader("Final group standings")
    st.caption("Q = qualified for Round of 32")
    cols = st.columns(4)
    for gi,(letter,teams) in enumerate(group_data.items()):
        with cols[gi % 4]:
            st.markdown(f"**Group {letter}**")
            df = pd.DataFrame(teams,columns=["Team","Pts","GD","Advanced"])
            df = df.sort_values(["Pts","GD"],ascending=False).reset_index(drop=True)
            for i,row in df.iterrows():
                color = "#4A90D9" if row["Advanced"] else "#666"
                adv   = " [Q]" if row["Advanced"] else ""
                st.markdown(
                    f"<div style='color:{color};font-size:13px;padding:2px 0'>"
                    f"{i+1}. {row['Team']} {row['Pts']}p "
                    f"GD{row['GD']:+d}{adv}</div>",
                    unsafe_allow_html=True
                )
            st.markdown("---")

# ── ROUND OF 32 ──
with tab2:
    st.subheader("Round of 32")

    done = []
    pending = []
    for date,home,away in r32_fixtures:
        key1 = (home, away)
        key2 = (away, home)
        if key1 in confirmed_r32:
            done.append((date,home,away,confirmed_r32[key1]))
        elif key2 in confirmed_r32:
            done.append((date,home,away,confirmed_r32[key2]))
        else:
            pred = r32_preds.get(key1, r32_preds.get(key2, None))
            pending.append((date,home,away,pred))

    if done:
        st.markdown(f"**Completed ({len(done)} matches)**")
        for date,home,away,result in done:
            winner  = result["winner"]
            method  = result["method"]
            hs      = result["home_score"]
            as_     = result["away_score"]
            correct = result.get("model_correct", None)
            is_pks  = "PK" in method
            is_upset = winner == away and any(
                u["match"] in f"{home} vs {away}" for u in upsets
            )
            bg     = "#3d0000" if is_upset else "#0d2d0d"
            border = "#ff4444" if is_upset else "#4A90D9"
            tag    = "UPSET" if is_upset else "Confirmed"
            acc    = "" if correct is None else (" - Model: correct" if correct else " - Model: missed")
            st.markdown(
                f"<div style='background:{bg};border-left:3px solid {border};"
                f"border-radius:6px;padding:10px 14px;margin:4px 0'>"
                f"<span style='color:#aaa;font-size:12px'>{date} - {tag}{acc}</span><br>"
                f"<span style='color:{'#ff6666' if is_upset else '#4A90D9'};"
                f"font-weight:600;font-size:14px'>{winner} advanced</span>"
                f"<span style='color:#888;font-size:13px'> &nbsp; "
                f"{home} {hs}-{as_} {away} ({method})</span>"
                f"</div>",
                unsafe_allow_html=True
            )

    if pending:
        st.divider()
        st.markdown(f"**Upcoming / Predicted ({len(pending)} matches)**")
        for i in range(0,len(pending),2):
            cols = st.columns(2)
            for j,item in enumerate(pending[i:i+2]):
                with cols[j]:
                    date,home,away,pred = item
                    if pred is None:
                        st.info(f"{date}: {home} vs {away} - prediction unavailable")
                        continue
                    hw     = pred["hw"]
                    aw     = pred["aw"]
                    conf   = pred["conf"]
                    winner = pred["winner"]
                    note   = "50/50" if conf <= 55 else "Likely" if conf <= 75 else "Strong favourite"
                    inj_home = injuries.get(home,{}).get("note","")
                    inj_away = injuries.get(away,{}).get("note","")
                    with st.container(border=True):
                        st.caption(f"{date} - V5 prediction - {note}")
                        c1,c2 = st.columns(2)
                        with c1:
                            color = "#4A90D9" if winner==home else "#666"
                            st.markdown(
                                f"<p style='color:{color};font-size:13px;"
                                f"font-weight:{'600' if winner==home else '400'}'>"
                                f"{'Predicted: ' if winner==home else ''}{home}</p>"
                                f"<p style='color:{color};font-size:22px;"
                                f"font-weight:600'>{hw}%</p>",
                                unsafe_allow_html=True
                            )
                            if inj_home:
                                st.caption(f"Injury: {inj_home}")
                        with c2:
                            color = "#4A90D9" if winner==away else "#666"
                            st.markdown(
                                f"<p style='color:{color};font-size:13px;"
                                f"font-weight:{'600' if winner==away else '400'}'>"
                                f"{'Predicted: ' if winner==away else ''}{away}</p>"
                                f"<p style='color:{color};font-size:22px;"
                                f"font-weight:600'>{aw}%</p>",
                                unsafe_allow_html=True
                            )
                            if inj_away:
                                st.caption(f"Injury: {inj_away}")
                        st.progress(hw/100)

# ── ROUND OF 16 ──
with tab3:
    st.subheader("Round of 16 - projected bracket")
    st.caption("Updated after Germany and Netherlands upsets. Paraguay and Morocco now in R16.")
    st.info(
        "R16 bracket will finalise as remaining R32 matches complete (Jul 1-3). "
        "Below reflects current confirmed R32 winners."
    )

    r16 = [
        ("Jul 4","Canada","Morocco",    45,55,55,"Morocco",   "Morocco upset Netherlands PKs"),
        ("Jul 4","Paraguay","France",   12,88,88,"France",    "Paraguay upset Germany PKs"),
        ("Jul 5","Brazil","Norway",     65,35,65,"Brazil",    "Haaland vs Vinicius"),
        ("Jul 5","Mexico","England",    18,82,82,"England",   "England strong favourite"),
        ("Jul 6","Portugal","Spain",    43,57,57,"Spain",     "Iberian derby"),
        ("Jul 6","USA","Belgium",       14,86,86,"Belgium",   "Belgium strong favourite"),
        ("Jul 7","Argentina","Australia",93,7,93,"Argentina", "Messi dominant"),
        ("Jul 7","Switzerland","Colombia",12,88,88,"Colombia","Colombia strong"),
    ]

    for i in range(0,len(r16),2):
        cols = st.columns(2)
        for j,m in enumerate(r16[i:i+2]):
            with cols[j]:
                date,home,away,hw,aw,conf,winner,note = m
                with st.container(border=True):
                    st.caption(f"{date} - {note} - Confidence {conf}%")
                    c1,c2 = st.columns(2)
                    with c1:
                        color = "#4A90D9" if winner==home else "#666"
                        st.markdown(
                            f"<p style='color:{color};font-size:13px;"
                            f"font-weight:{'600' if winner==home else '400'}'>"
                            f"{'Advances: ' if winner==home else ''}{home}</p>"
                            f"<p style='color:{color};font-size:22px;"
                            f"font-weight:600'>{hw}%</p>",
                            unsafe_allow_html=True
                        )
                    with c2:
                        color = "#4A90D9" if winner==away else "#666"
                        st.markdown(
                            f"<p style='color:{color};font-size:13px;"
                            f"font-weight:{'600' if winner==away else '400'}'>"
                            f"{'Advances: ' if winner==away else ''}{away}</p>"
                            f"<p style='color:{color};font-size:22px;"
                            f"font-weight:600'>{aw}%</p>",
                            unsafe_allow_html=True
                        )

# ── QF + SF ──
with tab4:
    qfc,sfc = st.columns([1.2,1])

    with qfc:
        st.subheader("Quarterfinals (Jul 9-11)")
        qf = [
            ("Jul 9", "Morocco","France",   15,85,85,"France"),
            ("Jul 9", "Brazil","England",   35,65,65,"England"),
            ("Jul 10","Spain","Belgium",    33,67,67,"Belgium"),
            ("Jul 10","Argentina","Colombia",92,8,92,"Argentina"),
        ]
        for date,home,away,hw,aw,conf,winner in qf:
            with st.container(border=True):
                st.caption(f"{date} - Confidence {conf}%")
                c1,c2 = st.columns(2)
                for team,pct,col in [(home,hw,c1),(away,aw,c2)]:
                    with col:
                        color = "#4A90D9" if winner==team else "#666"
                        st.markdown(
                            f"<div style='text-align:center'>"
                            f"<p style='color:{color};font-size:13px;"
                            f"font-weight:{'600' if winner==team else '400'}'>"
                            f"{'Advances ' if winner==team else ''}{team}</p>"
                            f"<p style='color:{color};font-size:22px;"
                            f"font-weight:600'>{pct}%</p></div>",
                            unsafe_allow_html=True
                        )

    with sfc:
        st.subheader("Semifinals (Jul 14-15)")
        sf = [
            ("Jul 14","France","England",  46,54,54,"England"),
            ("Jul 15","Belgium","Argentina",22,78,78,"Argentina"),
        ]
        for date,home,away,hw,aw,conf,winner in sf:
            with st.container(border=True):
                st.caption(f"{date} - Confidence {conf}%")
                c1,c2 = st.columns(2)
                for team,pct,col in [(home,hw,c1),(away,aw,c2)]:
                    with col:
                        color = "#4A90D9" if winner==team else "#666"
                        st.markdown(
                            f"<div style='text-align:center'>"
                            f"<p style='color:{color};font-size:13px;"
                            f"font-weight:{'600' if winner==team else '400'}'>"
                            f"{'Advances ' if winner==team else ''}{team}</p>"
                            f"<p style='color:{color};font-size:22px;"
                            f"font-weight:600'>{pct}%</p></div>",
                            unsafe_allow_html=True
                        )
        st.warning("England vs France: 54/46 - closest call in bracket")

# ── FINAL ──
with tab5:
    st.markdown(
        "<div style='text-align:center;padding:2rem 0 1rem'>"
        "<div style='font-size:56px'>*</div>"
        "<div style='font-size:28px;font-weight:600;color:#4A90D9'>England</div>"
        "<div style='font-size:14px;color:#888;margin-top:4px'>"
        "Predicted 2026 FIFA World Cup Champion</div>"
        "<div style='font-size:13px;color:#666;margin-top:2px'>"
        "55% probability to advance in the Final vs Argentina</div>"
        "</div>",
        unsafe_allow_html=True
    )
    fc1,fc2,fc3 = st.columns([1,2,1])
    with fc2:
        with st.container(border=True):
            st.caption("Final - Jul 19 - MetLife Stadium, New Jersey")
            tc1,tc2 = st.columns(2)
            with tc1:
                st.markdown(
                    "<div style='text-align:center'>"
                    "<p style='font-size:15px;font-weight:600;color:#4A90D9'>England</p>"
                    "<p style='font-size:32px;font-weight:600;color:#4A90D9'>55%</p>"
                    "<p style='font-size:12px;color:#888'>to advance</p></div>",
                    unsafe_allow_html=True
                )
            with tc2:
                st.markdown(
                    "<div style='text-align:center'>"
                    "<p style='font-size:15px;font-weight:600;color:#888'>Argentina</p>"
                    "<p style='font-size:32px;font-weight:600;color:#888'>45%</p>"
                    "<p style='font-size:12px;color:#666'>to advance</p></div>",
                    unsafe_allow_html=True
                )
            st.progress(0.55)

    st.divider()
    st.subheader("Predicted final standings")
    p1,p2,p3,p4 = st.columns(4)
    for col,pos,team,detail in [
        (p1,"Champion","England","55% in final"),
        (p2,"Runner-up","Argentina","45% in final"),
        (p3,"Third place","France","Lost semi 46-54"),
        (p4,"Fourth","Belgium","Lost semi 22-78"),
    ]:
        with col:
            with st.container(border=True):
                st.markdown(f"**{pos}**")
                st.markdown(f"### {team}")
                st.caption(detail)

    st.divider()
    st.caption(
        "Predictions: V5 XGBoost + FanDuel odds + injury flags. "
        "Knockout probabilities = chance of advancing (90min + ET + pens). "
        "Live data: ESPN API with 15-min cache. "
        "OOT accuracy on group stage: 71.0%."
    )
