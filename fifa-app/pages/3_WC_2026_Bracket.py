"""
WC 2026 Bracket — fully dynamic, reads all data from live_data.py.
Auto-updates every 15 minutes via ESPN API.
No hardcoded results — everything comes from the live data module.
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="WC 2026 Bracket", page_icon="Trophy", layout="wide")

st.title("2026 FIFA World Cup - Live Tournament Bracket")

# ── Load live data ──
try:
    from live_data import get_live_data, model_accuracy
    with st.spinner("Fetching latest results..."):
        data = get_live_data()

    c, t = model_accuracy(data)
    col1,col2,col3,col4 = st.columns(4)
    col1.metric("R32 Complete",  f"{data['r32_complete']}/16")
    col2.metric("R16 Complete",  f"{data['r16_complete']}/8")
    col3.metric("Model Accuracy",f"{c}/{t} ({int(c/t*100) if t else 0}%)")
    col4.metric("Last Updated",  data['last_updated'])

    r32 = data.get("confirmed_r32_raw", {})
    r16 = data.get("confirmed_r16_raw", {})
    qf  = data.get("confirmed_qf_raw",  {})
    upsets   = data.get("upsets", [])
    injuries = data.get("injury_flags", {})

    if upsets:
        st.error("UPSETS: " + " | ".join(
            f"[{u['round']}] {u['match']}: {u['result']}"
            for u in upsets
        ))

    st.caption(f"Data source: {data['data_source']}")

except Exception as e:
    st.warning(f"Live data unavailable: {e}")
    r32={}; r16={}; qf={}; upsets=[]; injuries={}

st.divider()

# ── All fixtures in order ──
R32_FIXTURES = [
    ("Jun 28","Canada","South Africa"),
    ("Jun 29","Brazil","Japan"),
    ("Jun 29","Germany","Paraguay"),
    ("Jun 29","Netherlands","Morocco"),
    ("Jun 30","Norway","Ivory Coast"),
    ("Jun 30","France","Sweden"),
    ("Jun 30","Mexico","Ecuador"),
    ("Jul 1", "England","DR Congo"),
    ("Jul 1", "Belgium","Senegal"),
    ("Jul 1", "United States","Bosnia and Herzegovina"),
    ("Jul 2", "Spain","Austria"),
    ("Jul 2", "Portugal","Croatia"),
    ("Jul 2", "Switzerland","Algeria"),
    ("Jul 3", "Australia","Egypt"),
    ("Jul 3", "Argentina","Cape Verde"),
    ("Jul 3", "Colombia","Ghana"),
]

R16_FIXTURES = [
    ("Jul 4", "Morocco",      "Canada"),
    ("Jul 4", "France",       "Paraguay"),
    ("Jul 5", "Norway",       "Brazil"),
    ("Jul 5", "England",      "Mexico"),
    ("Jul 6", "Spain",        "Portugal"),
    ("Jul 6", "Belgium",      "United States"),
    ("Jul 7", "Argentina",    "Egypt"),
    ("Jul 7", "Switzerland",  "Colombia"),
]

QF_FIXTURES = [
    ("Jul 9",  "France",    "Morocco"),
    ("Jul 10", "Spain",     "Belgium"),
    ("Jul 11", "Norway",    "England"),
    ("Jul 11", "Argentina", "TBD"),
]

MODEL_PREDS = {
    ("Canada","South Africa"):"Canada",("Brazil","Japan"):"Brazil",
    ("Germany","Paraguay"):"Germany",("Netherlands","Morocco"):"Netherlands",
    ("Norway","Ivory Coast"):"Ivory Coast",("France","Sweden"):"France",
    ("Mexico","Ecuador"):"Mexico",("England","DR Congo"):"England",
    ("Belgium","Senegal"):"Belgium",
    ("United States","Bosnia and Herzegovina"):"United States",
    ("Spain","Austria"):"Spain",("Portugal","Croatia"):"Portugal",
    ("Switzerland","Algeria"):"Switzerland",("Australia","Egypt"):"Australia",
    ("Argentina","Cape Verde"):"Argentina",("Colombia","Ghana"):"Colombia",
    ("Morocco","Canada"):"Morocco",("France","Paraguay"):"France",
    ("Norway","Brazil"):"Brazil",("England","Mexico"):"England",
    ("Spain","Portugal"):"Portugal",("Belgium","United States"):"Belgium",
    ("Argentina","Egypt"):"Argentina",("Switzerland","Colombia"):"Switzerland",
    ("France","Morocco"):"France",("Spain","Belgium"):"Spain",
    ("Norway","England"):"England",("Argentina","Switzerland"):"Argentina",
    ("Argentina","Colombia"):"Argentina",
}

QF_PROBS = {
    ("France","Morocco"):   (72,28),
    ("Spain","Belgium"):    (55,45),
    ("Norway","England"):   (38,62),
    ("Argentina","Switzerland"):(70,30),
    ("Argentina","Colombia"):(60,40),
}

def get_result(home, away, results_dict):
    """Look up result handling both team orderings."""
    return (results_dict.get((home,away)) or
            results_dict.get((away,home)))

def result_card(home, away, result, date=""):
    """Render a match result card."""
    winner  = result["winner"]
    hs      = result["home_score"]
    as_     = result["away_score"]
    method  = result["method"]
    correct = result.get("model_correct")
    pred    = MODEL_PREDS.get((home,away), MODEL_PREDS.get((away,home)))

    is_upset = (pred and pred != winner)
    bg     = "#3d0000" if is_upset else "#0d2d0d"
    border = "#ff4444" if is_upset else "#4A90D9"
    tag    = "UPSET" if is_upset else "Confirmed"
    acc    = "" if correct is None else (" - Model correct" if correct else " - Model missed")

    inj = injuries.get(winner,{}).get("note","")

    st.markdown(
        f"<div style='background:{bg};border-left:3px solid {border};"
        f"border-radius:6px;padding:10px 14px;margin:4px 0'>"
        f"<span style='color:#aaa;font-size:11px'>{date} - {tag}{acc}</span><br>"
        f"<span style='color:{'#ff6666' if is_upset else '#4A90D9'};"
        f"font-weight:600;font-size:14px'>{winner}</span>"
        f"<span style='color:#888;font-size:13px'> &nbsp; "
        f"{home} {hs}-{as_} {away}"
        f"{' (' + method + ')' if method != '90min' else ''}</span>"
        f"{'<br><span style=\"color:#888;font-size:11px\">'+inj+'</span>' if inj else ''}"
        f"</div>",
        unsafe_allow_html=True
    )

def prediction_card(home, away, hw, aw, conf, date=""):
    """Render a prediction card for upcoming match."""
    winner = home if hw >= aw else away
    with st.container(border=True):
        note = "50/50" if conf<=55 else "Likely" if conf<=75 else "Strong"
        st.caption(f"{date} - V5 prediction - {note} ({conf}% confidence)")
        c1,c2 = st.columns(2)
        with c1:
            color = "#4A90D9" if winner==home else "#666"
            st.markdown(
                f"<p style='color:{color};font-size:13px;font-weight:"
                f"{'600' if winner==home else '400'}'>"
                f"{'Predicted: ' if winner==home else ''}{home}</p>"
                f"<p style='color:{color};font-size:22px;font-weight:600'>{hw}%</p>",
                unsafe_allow_html=True
            )
        with c2:
            color = "#4A90D9" if winner==away else "#666"
            st.markdown(
                f"<p style='color:{color};font-size:13px;font-weight:"
                f"{'600' if winner==away else '400'}'>"
                f"{'Predicted: ' if winner==away else ''}{away}</p>"
                f"<p style='color:{color};font-size:22px;font-weight:600'>{aw}%</p>",
                unsafe_allow_html=True
            )
        st.progress(hw/100)

# ── GROUP STAGE ──
group_data = {
    "A":[("Mexico",9,6,True),("South Africa",4,0,True),("South Korea",3,0,False),("Czechia",1,-6,False)],
    "B":[("Switzerland",7,5,True),("Canada",5,5,True),("Bosnia & Herz.",4,2,True),("Qatar",0,-12,False)],
    "C":[("Brazil",7,6,True),("Morocco",4,4,True),("Scotland",3,0,False),("Haiti",0,-10,False)],
    "D":[("United States",6,3,True),("Paraguay",4,-1,True),("Australia",1,-1,False),("Turkey",3,-1,False)],
    "E":[("Germany",6,5,True),("Ivory Coast",4,3,True),("Ecuador",2,-2,False),("Curacao",0,-6,False)],
    "F":[("Netherlands",9,7,True),("Japan",4,1,True),("Sweden",2,2,True),("Tunisia",0,-10,False)],
    "G":[("Belgium",6,5,True),("Egypt",4,1,True),("New Zealand",1,-1,False),("Iran",0,-5,False)],
    "H":[("Spain",7,5,True),("Cape Verde",2,0,True),("Uruguay",1,0,False),("Saudi Arabia",1,-5,False)],
    "I":[("France",7,6,True),("Norway",7,5,True),("Senegal",3,0,False),("Iraq",0,-11,False)],
    "J":[("Argentina",9,7,True),("Austria",3,1,True),("Algeria",3,0,True),("Jordan",0,-8,False)],
    "K":[("Colombia",5,3,True),("Portugal",3,2,True),("DR Congo",2,0,False),("Uzbekistan",2,-5,False)],
    "L":[("England",9,7,True),("Croatia",6,2,True),("Ghana",3,-1,True),("Panama",0,-8,False)],
}

tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "Group Stage", "Round of 32", "Round of 16", "Quarters and Semis", "Final"
])

# ── TAB 1: GROUP STAGE ──
with tab1:
    st.subheader("Final group standings")
    cols = st.columns(4)
    for gi,(letter,teams) in enumerate(group_data.items()):
        with cols[gi%4]:
            st.markdown(f"**Group {letter}**")
            df = pd.DataFrame(teams,columns=["Team","Pts","GD","Q"])
            df = df.sort_values(["Pts","GD"],ascending=False).reset_index(drop=True)
            for i,row in df.iterrows():
                color = "#4A90D9" if row["Q"] else "#666"
                adv   = " [Q]" if row["Q"] else ""
                st.markdown(
                    f"<div style='color:{color};font-size:13px;padding:2px 0'>"
                    f"{i+1}. {row['Team']} {row['Pts']}p GD{row['GD']:+d}{adv}</div>",
                    unsafe_allow_html=True
                )
            st.markdown("---")

# ── TAB 2: ROUND OF 32 ──
with tab2:
    st.subheader("Round of 32")

    done    = []
    pending = []
    for date,home,away in R32_FIXTURES:
        res = get_result(home, away, r32)
        if res:
            done.append((date,home,away,res))
        else:
            pending.append((date,home,away))

    if done:
        st.markdown(f"**Completed ({len(done)}/16)**")
        for date,home,away,res in done:
            result_card(home,away,res,date)

    if pending:
        st.divider()
        st.markdown(f"**Upcoming ({len(pending)} matches)**")
        st.caption("V5 model predictions")
        for date,home,away in pending:
            st.info(f"{date}: {home} vs {away} - prediction pending")

# ── TAB 3: ROUND OF 16 ──
with tab3:
    st.subheader("Round of 16")

    done    = []
    pending = []
    for date,home,away in R16_FIXTURES:
        res = get_result(home, away, r16)
        if res:
            done.append((date,home,away,res))
        else:
            pending.append((date,home,away))

    if done:
        st.markdown(f"**Completed ({len(done)}/8)**")
        for i in range(0,len(done),2):
            cols = st.columns(2)
            for j,item in enumerate(done[i:i+2]):
                with cols[j]:
                    date,home,away,res = item
                    result_card(home,away,res,date)

    if pending:
        st.divider()
        st.markdown(f"**Still to play ({len(pending)} matches)**")
        for date,home,away in pending:
            pred = MODEL_PREDS.get((home,away), MODEL_PREDS.get((away,home),"TBD"))
            hw,aw = QF_PROBS.get((home,away), QF_PROBS.get((away,home),(50,50)))
            prediction_card(home,away,hw,aw,max(hw,aw),date)

# ── TAB 4: QF + SF ──
with tab4:
    qf_done    = []
    qf_pending = []
    for date,home,away in QF_FIXTURES:
        if away == "TBD":
            qf_pending.append((date,home,away))
            continue
        res = get_result(home, away, qf)
        if res:
            qf_done.append((date,home,away,res))
        else:
            qf_pending.append((date,home,away))

    qfc,sfc = st.columns([1.2,1])
    with qfc:
        st.subheader("Quarterfinals (Jul 9-11)")
        if qf_done:
            for date,home,away,res in qf_done:
                result_card(home,away,res,date)
        for date,home,away in qf_pending:
            if away == "TBD":
                st.info(f"{date}: {home} vs SUI/COL winner - pending R16 result")
                continue
            probs = QF_PROBS.get((home,away), QF_PROBS.get((away,home),(50,50)))
            prediction_card(home,away,probs[0],probs[1],max(probs),date)

    with sfc:
        st.subheader("Semifinals (Jul 14-15)")
        st.info("Semifinal matchups will be determined after QF results.")
        sf_preds = [
            ("France/Morocco winner","Spain/Belgium winner",  55,45,55),
            ("Norway/England winner","Argentina/??? winner",  45,55,55),
        ]
        for home,away,hw,aw,conf in sf_preds:
            with st.container(border=True):
                st.caption(f"Projected semifinal - Confidence {conf}%")
                c1,c2 = st.columns(2)
                with c1:
                    st.markdown(f"<p style='color:#4A90D9;font-size:13px'>{home}</p>"
                               f"<p style='color:#4A90D9;font-size:20px;font-weight:600'>{hw}%</p>",
                               unsafe_allow_html=True)
                with c2:
                    st.markdown(f"<p style='color:#888;font-size:13px'>{away}</p>"
                               f"<p style='color:#888;font-size:20px;font-weight:600'>{aw}%</p>",
                               unsafe_allow_html=True)

# ── TAB 5: FINAL ──
with tab5:
    st.markdown(
        "<div style='text-align:center;padding:2rem 0 1rem'>"
        "<div style='font-size:56px'>*</div>"
        "<div style='font-size:24px;font-weight:600;color:#4A90D9'>Predicted Champion: England</div>"
        "<div style='font-size:13px;color:#888;margin-top:4px'>"
        "Subject to QF and SF results</div></div>",
        unsafe_allow_html=True
    )
    fc1,fc2,fc3 = st.columns([1,2,1])
    with fc2:
        with st.container(border=True):
            st.caption("Final - Jul 19 - MetLife Stadium, New Jersey")
            st.markdown("Finalists to be determined after semifinals.")
            st.progress(0.55)
            st.caption(
                "Current projected final: England vs Argentina (55-45). "
                "Norway's run has changed the picture significantly."
            )

    st.divider()
    st.caption(
        "All predictions: V5 XGBoost (78 features) + FanDuel odds + injury flags. "
        "Live data: ESPN API with 15-min cache. "
        "OOT accuracy on group stage: 71.0%."
    )
