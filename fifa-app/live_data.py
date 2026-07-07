"""
live_data.py
============
Fetches 2026 WC results automatically from ESPN API.
Tries each match day individually (ESPN scoreboard works per-date).
Falls back to verified snapshot if API unavailable.
Cache TTL: 15 minutes.

Last snapshot update: July 7, 2026 - All R32 done, R16 7/8 done.
Switzerland vs Colombia result will auto-fetch via ESPN.
"""
import requests, json, datetime
from pathlib import Path

CACHE_FILE = Path(__file__).parent / ".wc_cache.json"
CACHE_TTL  = 900  # 15 minutes

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.espn.com/",
    "Origin": "https://www.espn.com",
}

ESPN_NAME_MAP = {
    "United States":                    "United States",
    "USA":                              "United States",
    "Bosnia-Herzegovina":               "Bosnia and Herzegovina",
    "Bosnia & Herzegovina":             "Bosnia and Herzegovina",
    "Ivory Coast":                      "Ivory Coast",
    "Cote d'Ivoire":                    "Ivory Coast",
    "Côte d'Ivoire":                    "Ivory Coast",
    "DR Congo":                         "DR Congo",
    "Congo DR":                         "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
    "Korea Republic":                   "South Korea",
    "Czech Republic":                   "Czechia",
    "Cape Verde":                       "Cape Verde",
    "Cabo Verde":                       "Cape Verde",
    "Cape Verde Islands":               "Cape Verde",
    "Egypt":                            "Egypt",
    "Norway":                           "Norway",
    "Morocco":                          "Morocco",
    "Paraguay":                         "Paraguay",
    "Argentina":                        "Argentina",
    "Colombia":                         "Colombia",
    "Switzerland":                      "Switzerland",
}

def normalise(name):
    return ESPN_NAME_MAP.get(name, name)

# ── ALL KNOCKOUT MATCH DATES ──
WC_KNOCKOUT_DATES = [
    "20260628", "20260629", "20260630",
    "20260701", "20260702", "20260703",
    "20260704", "20260705", "20260706", "20260707",
    "20260709", "20260710", "20260711",
    "20260714", "20260715",
    "20260718", "20260719",
]

# ── VERIFIED SNAPSHOT — all confirmed results ──
VERIFIED_R32 = {
    ("Canada",       "South Africa"):           (1,0,"Canada",        "90min", True),
    ("Brazil",       "Japan"):                  (2,1,"Brazil",        "90min", True),
    ("Germany",      "Paraguay"):               (1,1,"Paraguay",      "PKs 4-3",False),
    ("Netherlands",  "Morocco"):                (1,1,"Morocco",       "PKs 3-2",False),
    ("Norway",       "Ivory Coast"):            (2,1,"Norway",        "90min", False),
    ("France",       "Sweden"):                 (3,0,"France",        "90min", True),
    ("Mexico",       "Ecuador"):                (2,0,"Mexico",        "90min", True),
    ("England",      "DR Congo"):               (2,1,"England",       "90min", True),
    ("Belgium",      "Senegal"):                (3,2,"Belgium",       "AET",   True),
    ("United States","Bosnia and Herzegovina"): (2,0,"United States", "90min", True),
    ("Spain",        "Austria"):                (3,0,"Spain",         "90min", True),
    ("Portugal",     "Croatia"):                (2,1,"Portugal",      "90min", True),
    ("Switzerland",  "Algeria"):                (2,0,"Switzerland",   "90min", True),
    ("Australia",    "Egypt"):                  (1,1,"Egypt",         "PKs 4-2",False),
    ("Argentina",    "Cape Verde"):             (3,2,"Argentina",     "AET",   True),
    ("Colombia",     "Ghana"):                  (1,0,"Colombia",      "90min", True),
}

VERIFIED_R16 = {
    ("Morocco",      "Canada"):        (3,0,"Morocco",       "90min", True),
    ("France",       "Paraguay"):      (1,0,"France",        "90min", True),
    ("Norway",       "Brazil"):        (2,1,"Norway",        "90min", False),
    ("England",      "Mexico"):        (3,2,"England",       "90min", True),
    ("Spain",        "Portugal"):      (1,0,"Spain",         "90min", False),
    ("Belgium",      "United States"): (4,1,"Belgium",       "90min", True),
    ("Argentina",    "Egypt"):         (3,2,"Argentina",     "90min", True),
    # Switzerland vs Colombia — ESPN API will add this automatically
}

MODEL_PREDICTIONS = {
    # R32
    ("Canada","South Africa"):"Canada",
    ("Brazil","Japan"):"Brazil",
    ("Germany","Paraguay"):"Germany",
    ("Netherlands","Morocco"):"Netherlands",
    ("Norway","Ivory Coast"):"Ivory Coast",
    ("France","Sweden"):"France",
    ("Mexico","Ecuador"):"Mexico",
    ("England","DR Congo"):"England",
    ("Belgium","Senegal"):"Belgium",
    ("United States","Bosnia and Herzegovina"):"United States",
    ("Spain","Austria"):"Spain",
    ("Portugal","Croatia"):"Portugal",
    ("Switzerland","Algeria"):"Switzerland",
    ("Australia","Egypt"):"Australia",
    ("Argentina","Cape Verde"):"Argentina",
    ("Colombia","Ghana"):"Colombia",
    # R16
    ("Morocco","Canada"):"Morocco",
    ("France","Paraguay"):"France",
    ("Norway","Brazil"):"Brazil",
    ("England","Mexico"):"England",
    ("Spain","Portugal"):"Portugal",
    ("Belgium","United States"):"Belgium",
    ("Argentina","Egypt"):"Argentina",
    ("Switzerland","Colombia"):"Switzerland",
    # QF predictions
    ("France","Morocco"):"France",
    ("Spain","Belgium"):"Spain",
    ("Norway","England"):"England",
    ("Argentina","Switzerland"):"Argentina",
    ("Argentina","Colombia"):"Argentina",
}

QF_PREDICTIONS = {
    ("France","Morocco"):     {"hw":72,"aw":28,"conf":72,"winner":"France"},
    ("Spain","Belgium"):      {"hw":55,"aw":45,"conf":55,"winner":"Spain"},
    ("Norway","England"):     {"hw":38,"aw":62,"conf":62,"winner":"England"},
    ("Argentina","Switzerland"):{"hw":70,"aw":30,"conf":70,"winner":"Argentina"},
    ("Argentina","Colombia"): {"hw":60,"aw":40,"conf":60,"winner":"Argentina"},
}

INJURY_FLAGS = {
    "Brazil":    {"impact":-0.08,"note":"ELIMINATED R16 by Norway 2-1"},
    "England":   {"impact":-0.06,"note":"Kane fit; Bellingham in form"},
    "Spain":     {"impact":-0.10,"note":"Nico Williams out; Yamal fit"},
    "Norway":    {"impact": 0.05,"note":"Haaland 6 goals - joint Golden Boot leader"},
    "Argentina": {"impact":-0.02,"note":"Messi 8 goals - Golden Boot leader"},
    "Morocco":   {"impact":-0.05,"note":"En-Nesyri scoring; strong defence"},
    "Portugal":  {"impact": 0.00,"note":"ELIMINATED R16. Ronaldo retired from intl football"},
    "Belgium":   {"impact": 0.00,"note":"Lukaku 3 goals; De Bruyne fit"},
    "France":    {"impact": 0.00,"note":"Mbappe 7 goals; Griezmann fit"},
    "Colombia":  {"impact":-0.05,"note":"Luis Diaz hamstring concern"},
    "Switzerland":{"impact":-0.08,"note":"Manzambi injury doubt for QF"},
}

UPSETS = [
    {"match":"Germany vs Paraguay",     "result":"Paraguay PKs 4-3",    "round":"R32","severity":"historic"},
    {"match":"Netherlands vs Morocco",  "result":"Morocco PKs 3-2",     "round":"R32","severity":"historic"},
    {"match":"Australia vs Egypt",      "result":"Egypt PKs 4-2",       "round":"R32","severity":"major"},
    {"match":"Norway vs Brazil",        "result":"Norway win 2-1",      "round":"R16","severity":"historic"},
    {"match":"Spain vs Portugal",       "result":"Spain 1-0 - Ronaldo out","round":"R16","severity":"major"},
    {"match":"Argentina vs Egypt",      "result":"3-2 comeback from 2-0","round":"R16","severity":"drama"},
]

HOST_NATIONS = {"United States","Mexico","Canada"}

def is_neutral(home, stage):
    if stage in ("R32","R16","QF","SF","F"): return True
    return home not in HOST_NATIONS


def _fetch_espn_all_dates():
    """
    Fetch completed WC matches from ESPN one date at a time.
    This is more reliable than date ranges.
    """
    results = {}
    session = requests.Session()
    session.headers.update(HEADERS)

    for date in WC_KNOCKOUT_DATES:
        try:
            url = (
                f"https://site.api.espn.com/apis/site/v2/sports/soccer"
                f"/fifa.world/scoreboard?dates={date}&limit=20"
            )
            r = session.get(url, timeout=6)
            if r.status_code != 200:
                continue

            events = r.json().get("events", [])
            for event in events:
                stype = event.get("status",{}).get("type",{})
                if not stype.get("completed", False):
                    continue

                comps = event.get("competitions",[{}])[0]
                competitors = comps.get("competitors",[])
                if len(competitors) != 2:
                    continue

                hc = next((c for c in competitors if c.get("homeAway")=="home"), competitors[0])
                ac = next((c for c in competitors if c.get("homeAway")=="away"), competitors[1])

                hn = normalise(hc.get("team",{}).get("displayName",""))
                an = normalise(ac.get("team",{}).get("displayName",""))

                try:
                    hs  = int(hc.get("score","0") or 0)
                    as_ = int(ac.get("score","0") or 0)
                except:
                    continue

                notes  = comps.get("notes",[])
                method = "90min"
                for n in notes:
                    h = n.get("headline","").lower()
                    if "penalt" in h or "pk" in h: method="PKs"; break
                    if "extra" in h or "aet" in h: method="AET"; break

                winner = hn if hs > as_ else an
                if hs == as_:
                    for comp in competitors:
                        if comp.get("winner",False):
                            winner = normalise(comp.get("team",{}).get("displayName",""))
                            break

                if hn and an:
                    results[(hn,an)] = {
                        "home":hn,"away":an,
                        "home_score":hs,"away_score":as_,
                        "winner":winner,"method":method,
                        "source":"espn_api",
                    }
        except:
            continue

    return results


def get_live_data(force_refresh=False):
    # Check cache
    if not force_refresh and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            age   = datetime.datetime.now().timestamp() - cache.get("ts",0)
            if age < CACHE_TTL:
                return cache["data"]
        except:
            pass

    # Build from snapshot
    r32 = {}
    for (h,a),(hs,as_,winner,method,correct) in VERIFIED_R32.items():
        r32[(h,a)] = {"home":h,"away":a,"home_score":hs,"away_score":as_,
                      "winner":winner,"method":method,"source":"snapshot",
                      "model_correct":correct,"round":"R32"}

    r16 = {}
    for (h,a),(hs,as_,winner,method,correct) in VERIFIED_R16.items():
        r16[(h,a)] = {"home":h,"away":a,"home_score":hs,"away_score":as_,
                      "winner":winner,"method":method,"source":"snapshot",
                      "model_correct":correct,"round":"R16"}

    qf  = {}
    api_source = "verified snapshot (Jul 7 2026)"

    # Try ESPN per-date fetch
    espn = _fetch_espn_all_dates()
    if espn:
        for key,result in espn.items():
            h,a = key
            pred = (MODEL_PREDICTIONS.get((h,a)) or
                    MODEL_PREDICTIONS.get((a,h)))
            result["model_correct"] = (pred==result["winner"]) if pred else None

            # Route to correct round bucket
            if key in r32 or (a,h) in r32:
                r32[key] = result
            elif key in r16 or (a,h) in r16:
                r16[key] = result
            else:
                # New result not in snapshot — could be QF/SF/Final or SUI vs COL
                qf[key] = result

        api_source = f"ESPN API ({len(espn)} matches) + snapshot"

    # Compute accuracy
    all_results = {**r32,**r16,**qf}
    total   = len(all_results)
    correct = sum(1 for v in all_results.values() if v.get("model_correct") is True)

    # Build upsets dynamically (model got it wrong)
    dynamic_upsets = list(UPSETS)  # start from known
    for key,res in {**r16,**qf}.items():
        pred = (MODEL_PREDICTIONS.get(key) or
                MODEL_PREDICTIONS.get((key[1],key[0])))
        if pred and pred != res["winner"]:
            match_str = f"{key[0]} vs {key[1]}"
            if not any(u["match"]==match_str for u in dynamic_upsets):
                dynamic_upsets.append({
                    "match":   match_str,
                    "result":  f"{res['winner']} win ({res['method']})",
                    "round":   res.get("round","KO"),
                    "severity":"major",
                })

    data = {
        "confirmed_r32_raw":  r32,
        "confirmed_r16_raw":  r16,
        "confirmed_qf_raw":   qf,
        "r16_predictions":    {str(k):v for k,v in QF_PREDICTIONS.items()},
        "qf_predictions":     QF_PREDICTIONS,
        "injury_flags":       INJURY_FLAGS,
        "upsets":             dynamic_upsets,
        "last_updated":       datetime.datetime.now().strftime("%b %d %H:%M ET"),
        "r32_complete":       len(r32),
        "r32_total":          16,
        "r16_complete":       len(r16),
        "r16_total":          8,
        "qf_complete":        len(qf),
        "model_correct":      correct,
        "model_total":        total,
        "data_source":        api_source,
        "current_round":      "Quarterfinals (Jul 9-11)",
        "golden_boot_leader": "Messi (Argentina) - 8 goals",
    }

    try:
        CACHE_FILE.write_text(
            json.dumps({"ts":datetime.datetime.now().timestamp(),"data":data},default=str),
            encoding="utf-8"
        )
    except:
        pass

    return data


def model_accuracy(data):
    return data.get("model_correct",0), data.get("model_total",0)


if __name__ == "__main__":
    import sys
    data = get_live_data(force_refresh="--refresh" in sys.argv)
    print(f"Source:  {data['data_source']}")
    print(f"Updated: {data['last_updated']}")
    print(f"R32: {data['r32_complete']}/16 | R16: {data['r16_complete']}/8 | QF: {data['qf_complete']}/4")
    c,t = model_accuracy(data)
    print(f"Model:   {c}/{t} ({int(c/t*100) if t else 0}%)")
    print(f"\nUpsets:")
    for u in data["upsets"]:
        print(f"  [{u['round']}] {u['match']}: {u['result']}")


def compute_round_accuracy(data):
    """
    Compute model accuracy broken down by tournament round.
    Returns dict with per-round stats.
    """
    rounds = {
        "Group Stage": {"correct":0,"total":0,"results":[]},
        "Round of 32": {"correct":0,"total":0,"results":[]},
        "Round of 16": {"correct":0,"total":0,"results":[]},
        "Quarterfinals":{"correct":0,"total":0,"results":[]},
        "Semifinals":   {"correct":0,"total":0,"results":[]},
        "Final":        {"correct":0,"total":0,"results":[]},
    }

    # Group stage — hardcoded from our OOT validation
    group_results = [
        ("Mexico","South Africa","Home Win","Home Win",True),
        ("South Korea","Czechia","Home Win","Away Win",False),
        ("Canada","Bosnia and Herzegovina","Draw","Draw",True),
        ("Qatar","Switzerland","Draw","Draw",True),
        ("Brazil","Morocco","Draw","Away Win",False),
        ("Haiti","Scotland","Away Win","Away Win",True),
        ("United States","Paraguay","Home Win","Home Win",True),
        ("Australia","Turkey","Home Win","Away Win",False),
        ("Ecuador","Germany","Away Win","Away Win",True),
        ("Curacao","Ivory Coast","Away Win","Away Win",True),
        ("Netherlands","Japan","Draw","Away Win",False),
        ("Sweden","Tunisia","Home Win","Home Win",True),
        ("Belgium","Egypt","Draw","Home Win",False),
        ("Iran","New Zealand","Draw","Home Win",False),
        ("Spain","Cape Verde","Draw","Home Win",False),
        ("Saudi Arabia","Uruguay","Draw","Away Win",False),
        ("Norway","France","Away Win","Away Win",True),
        ("Senegal","Iraq","Home Win","Home Win",True),
        ("Algeria","Austria","Home Win","Away Win",False),
        ("Jordan","Argentina","Away Win","Away Win",True),
        ("Colombia","Uzbekistan","Home Win","Home Win",True),
        ("Portugal","DR Congo","Draw","Home Win",False),
        ("Panama","England","Away Win","Away Win",True),
        ("Croatia","Ghana","Away Win","Away Win",True),
        ("France","Senegal","Home Win","Home Win",True),
        ("Iraq","Norway","Away Win","Away Win",True),
        ("Argentina","Algeria","Home Win","Home Win",True),
        ("Austria","Jordan","Home Win","Home Win",True),
        ("Uzbekistan","Colombia","Away Win","Away Win",True),
        ("England","Croatia","Home Win","Home Win",True),
        ("Ghana","Panama","Home Win","Home Win",True),
    ]

    for home,away,actual,predicted,correct in group_results:
        rounds["Group Stage"]["total"]   += 1
        rounds["Group Stage"]["correct"] += int(correct)
        rounds["Group Stage"]["results"].append({
            "home":home,"away":away,
            "actual":actual,"predicted":predicted,"correct":correct
        })

    # R32 from live data
    for (h,a),res in data.get("confirmed_r32_raw",{}).items():
        correct = res.get("model_correct", False)
        rounds["Round of 32"]["total"]   += 1
        rounds["Round of 32"]["correct"] += int(correct) if correct else 0
        rounds["Round of 32"]["results"].append({
            "home":h,"away":a,
            "winner":res["winner"],"method":res["method"],
            "correct":correct
        })

    # R16 from live data
    for (h,a),res in data.get("confirmed_r16_raw",{}).items():
        correct = res.get("model_correct", False)
        rounds["Round of 16"]["total"]   += 1
        rounds["Round of 16"]["correct"] += int(correct) if correct else 0
        rounds["Round of 16"]["results"].append({
            "home":h,"away":a,
            "winner":res["winner"],"method":res["method"],
            "correct":correct
        })

    # QF from live data
    for (h,a),res in data.get("confirmed_qf_raw",{}).items():
        correct = res.get("model_correct", False)
        rounds["Quarterfinals"]["total"]   += 1
        rounds["Quarterfinals"]["correct"] += int(correct) if correct else 0
        rounds["Quarterfinals"]["results"].append({
            "home":h,"away":a,
            "winner":res["winner"],"method":res["method"],
            "correct":correct
        })

    # Compute accuracy per round
    summary = {}
    total_correct = 0
    total_matches = 0
    for round_name, stats in rounds.items():
        t = stats["total"]
        c = stats["correct"]
        if t > 0:
            summary[round_name] = {
                "correct":  c,
                "total":    t,
                "accuracy": round(c/t*100, 1),
                "results":  stats["results"]
            }
            total_correct += c
            total_matches += t

    summary["Overall"] = {
        "correct":  total_correct,
        "total":    total_matches,
        "accuracy": round(total_correct/total_matches*100,1) if total_matches else 0,
    }

    return summary
