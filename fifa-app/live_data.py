"""
live_data.py
============
Auto-fetches 2026 WC results from ESPN public API.
Verified snapshot updated July 2, 2026 with all confirmed R32 results.
Falls back to snapshot if API unavailable. Cache TTL: 15 minutes.
"""
import requests, json, datetime
from pathlib import Path

CACHE_FILE = Path(__file__).parent / ".wc_cache.json"
CACHE_TTL  = 900  # 15 minutes

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
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
}

def normalise(name):
    return ESPN_NAME_MAP.get(name, name)

# ── FULLY VERIFIED R32 RESULTS ──
# Source: Yahoo Sports, CBS Sports, NBC Sports, Sky Sports
# Verified: July 2, 2026
# Format: (home_score, away_score, winner, method, model_correct)
VERIFIED_RESULTS = {
    # CONFIRMED COMPLETED
    ("Canada",       "South Africa"):           (1,0,"Canada",             "90min", True),
    ("Brazil",       "Japan"):                  (2,1,"Brazil",             "90min", True),
    ("Germany",      "Paraguay"):               (1,1,"Paraguay",           "PKs",   False),  # UPSET - model had Germany
    ("Netherlands",  "Morocco"):                (1,1,"Morocco",            "PKs",   False),  # UPSET - model had Netherlands
    ("Norway",       "Ivory Coast"):            (2,1,"Norway",             "90min", False),  # model had Ivory Coast
    ("France",       "Sweden"):                 (3,0,"France",             "90min", True),
    ("Mexico",       "Ecuador"):                (2,0,"Mexico",             "90min", True),
    ("England",      "DR Congo"):               (2,1,"England",            "90min", True),
    ("Belgium",      "Senegal"):                (3,2,"Belgium",            "AET",   True),   # Belgium won AET 3-2
    ("United States","Bosnia and Herzegovina"): (2,0,"United States",      "90min", True),
    # STILL TO PLAY July 2-3
    # ("Spain",       "Austria")
    # ("Portugal",    "Croatia")
    # ("Switzerland", "Algeria")
    # ("Australia",   "Egypt")
    # ("Argentina",   "Cape Verde")
    # ("Colombia",    "Ghana")
}

MODEL_PREDICTIONS = {
    ("Canada",       "South Africa"):           "Canada",
    ("Brazil",       "Japan"):                  "Brazil",
    ("Germany",      "Paraguay"):               "Germany",
    ("Netherlands",  "Morocco"):                "Netherlands",
    ("Norway",       "Ivory Coast"):            "Ivory Coast",
    ("France",       "Sweden"):                 "France",
    ("Mexico",       "Ecuador"):                "Mexico",
    ("England",      "DR Congo"):               "England",
    ("Belgium",      "Senegal"):                "Belgium",
    ("United States","Bosnia and Herzegovina"): "United States",
    ("Spain",        "Austria"):                "Spain",
    ("Portugal",     "Croatia"):                "Portugal",
    ("Switzerland",  "Algeria"):                "Switzerland",
    ("Australia",    "Egypt"):                  "Australia",
    ("Argentina",    "Cape Verde"):             "Argentina",
    ("Colombia",     "Ghana"):                  "Colombia",
}

# R16 matchups confirmed from R32 results
R16_MATCHUPS = [
    ("Jul 4", "1 PM ET",  "Canada",       "Morocco",              "Houston",       True),
    ("Jul 4", "5 PM ET",  "Paraguay",     "France",               "Philadelphia",  True),
    ("Jul 5", "4 PM ET",  "Brazil",       "Norway",               "East Rutherford",True),
    ("Jul 5", "8 PM ET",  "Mexico",       "England",              "Mexico City",   False),  # Mexico home
    ("Jul 6", "3 PM ET",  "TBD",          "TBD",                  "Dallas",        True),   # Spain/Austria vs Portugal/Croatia
    ("Jul 6", "8 PM ET",  "United States","Belgium",              "Seattle",       False),  # USA home
    ("Jul 7", "12 PM ET", "TBD",          "TBD",                  "Atlanta",       True),   # Argentina/Cape Verde vs Australia/Egypt
    ("Jul 7", "4 PM ET",  "TBD",          "TBD",                  "Kansas City",   True),   # Switzerland/Algeria vs Colombia/Ghana
]

R16_PREDICTIONS = {
    ("Canada",        "Morocco"):        {"hw":45,"aw":55,"conf":55,"winner":"Morocco"},
    ("Paraguay",      "France"):         {"hw":12,"aw":88,"conf":88,"winner":"France"},
    ("Brazil",        "Norway"):         {"hw":65,"aw":35,"conf":65,"winner":"Brazil"},
    ("Mexico",        "England"):        {"hw":35,"aw":65,"conf":65,"winner":"England"},
    ("United States", "Belgium"):        {"hw":14,"aw":86,"conf":86,"winner":"Belgium"},
}

R32_PREDICTIONS = {
    ("Spain",        "Austria"):         {"hw":90,"aw":10,"conf":90,"winner":"Spain"},
    ("Portugal",     "Croatia"):         {"hw":65,"aw":35,"conf":65,"winner":"Portugal"},
    ("Switzerland",  "Algeria"):         {"hw":60,"aw":40,"conf":60,"winner":"Switzerland"},
    ("Australia",    "Egypt"):           {"hw":51,"aw":49,"conf":51,"winner":"Australia"},
    ("Argentina",    "Cape Verde"):      {"hw":94,"aw":6, "conf":94,"winner":"Argentina"},
    ("Colombia",     "Ghana"):           {"hw":87,"aw":13,"conf":87,"winner":"Colombia"},
}

INJURY_FLAGS = {
    "Brazil":         {"impact":-0.08,"note":"Rodrygo (ACL), Estevao out; Neymar fit"},
    "England":        {"impact":-0.06,"note":"Reece James doubtful; Kane fit"},
    "Spain":          {"impact":-0.12,"note":"Nico Williams + Yeremy Pino both out"},
    "Japan":          {"impact":-0.10,"note":"Mitoma + Minamino both out - ELIMINATED"},
    "Austria":        {"impact":-0.08,"note":"Baumgartner out"},
    "Morocco":        {"impact":-0.05,"note":"Ezzalzouli out"},
    "Argentina":      {"impact":-0.02,"note":"Panichelli out; Messi fit"},
    "Norway":         {"impact": 0.00,"note":"Haaland fit - 5 goals in tournament"},
    "Paraguay":       {"impact": 0.05,"note":"Beat Germany PKs - momentum shift"},
    "Mexico":         {"impact":-0.03,"note":"Montes suspended for R16 vs England"},
    "United States":  {"impact":-0.05,"note":"Balogun suspended (red card vs Bosnia)"},
}

HOST_NATIONS = {"United States", "Mexico", "Canada"}

def is_neutral(home, stage):
    if stage in ("R32","R16","QF","SF","F"):
        return True
    return home not in HOST_NATIONS


def _fetch_espn_date_range():
    """Fetch completed WC matches from ESPN API across full date range."""
    results = {}
    date_ranges = [
        "20260628-20260630",
        "20260701-20260703",
        "20260704-20260710",
        "20260711-20260719",
    ]
    for date_range in date_ranges:
        try:
            url = (
                f"https://site.api.espn.com/apis/site/v2/sports/soccer"
                f"/fifa.world/scoreboard?limit=50&dates={date_range}"
            )
            r = requests.get(url, headers=HEADERS, timeout=8)
            r.raise_for_status()
            events = r.json().get("events", [])
            for event in events:
                stype = event.get("status",{}).get("type",{})
                if not stype.get("completed", False):
                    continue
                comps = event.get("competitions",[{}])[0]
                competitors = comps.get("competitors",[])
                if len(competitors) != 2:
                    continue
                home_c = next((c for c in competitors if c.get("homeAway")=="home"), competitors[0])
                away_c = next((c for c in competitors if c.get("homeAway")=="away"), competitors[1])
                home_name = normalise(home_c.get("team",{}).get("displayName",""))
                away_name = normalise(away_c.get("team",{}).get("displayName",""))
                try:
                    hs  = int(home_c.get("score","0") or 0)
                    as_ = int(away_c.get("score","0") or 0)
                except (ValueError, TypeError):
                    continue
                notes  = comps.get("notes",[])
                method = "90min"
                for n in notes:
                    h = n.get("headline","").lower()
                    if "penalt" in h or "pk" in h: method="PKs"; break
                    if "extra" in h or "aet" in h: method="AET"; break
                winner = home_name if hs > as_ else away_name
                if hs == as_:
                    for comp in competitors:
                        if comp.get("winner",False):
                            winner = normalise(comp.get("team",{}).get("displayName",""))
                            break
                if home_name and away_name:
                    results[(home_name,away_name)] = {
                        "home":home_name,"away":away_name,
                        "home_score":hs,"away_score":as_,
                        "winner":winner,"method":method,"source":"espn_api",
                    }
        except Exception:
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
        except Exception:
            pass

    # Build from snapshot
    confirmed = {}
    for (home,away),(hs,as_,winner,method,correct) in VERIFIED_RESULTS.items():
        confirmed[(home,away)] = {
            "home":home,"away":away,
            "home_score":hs,"away_score":as_,
            "winner":winner,"method":method,
            "source":"snapshot","model_correct":correct,
        }

    api_source = "verified snapshot (Jul 2 2026)"

    # Try ESPN API
    espn = _fetch_espn_date_range()
    if espn:
        for key,result in espn.items():
            home,away = key
            pred = MODEL_PREDICTIONS.get((home,away), MODEL_PREDICTIONS.get((away,home)))
            result["model_correct"] = (pred==result["winner"]) if pred else None
            confirmed[key] = result
        api_source = f"ESPN API ({len(espn)} matches) + snapshot"

    # Build upsets
    upsets = []
    for (home,away),res in confirmed.items():
        pred = MODEL_PREDICTIONS.get((home,away), MODEL_PREDICTIONS.get((away,home)))
        if pred and pred != res["winner"]:
            upsets.append({
                "match":    f"{home} vs {away}",
                "result":   f"{res['winner']} advanced ({res['method']})",
                "severity": "major" if res["method"]=="PKs" else "standard",
            })

    total   = len(confirmed)
    correct = sum(1 for v in confirmed.values() if v.get("model_correct") is True)

    data = {
        "confirmed_r32_raw": confirmed,
        "r32_predictions":   R32_PREDICTIONS,
        "r16_predictions":   R16_PREDICTIONS,
        "r16_matchups":      R16_MATCHUPS,
        "injury_flags":      INJURY_FLAGS,
        "upsets":            upsets,
        "last_updated":      datetime.datetime.now().strftime("%b %d %H:%M ET"),
        "r32_complete":      total,
        "r32_total":         16,
        "model_correct":     correct,
        "model_total":       total,
        "data_source":       api_source,
    }

    try:
        CACHE_FILE.write_text(
            json.dumps({"ts":datetime.datetime.now().timestamp(),"data":data},default=str),
            encoding="utf-8"
        )
    except Exception:
        pass

    return data


def model_accuracy_r32(data):
    return data.get("model_correct",0), data.get("model_total",0)


if __name__ == "__main__":
    import sys
    data = get_live_data(force_refresh="--refresh" in sys.argv)
    print(f"Source:   {data['data_source']}")
    print(f"Updated:  {data['last_updated']}")
    print(f"R32 done: {data['r32_complete']}/{data['r32_total']}")
    c,t = model_accuracy_r32(data)
    print(f"Accuracy: {c}/{t} ({int(c/t*100) if t else 0}%)")
    print(f"Upsets:   {[u['match']+': '+u['result'] for u in data['upsets']]}")
