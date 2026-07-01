"""
live_data.py
============
Auto-fetches 2026 WC results from ESPN public API.
No manual updates needed — just run the app and results
populate automatically as matches complete.

Cache: 15 minutes (auto-refreshes in background).
Fallback: verified snapshot if API unavailable.
"""
import requests, json, datetime, re
from pathlib import Path

CACHE_FILE = Path(__file__).parent / ".wc_cache.json"
CACHE_TTL  = 900   # 15 minutes

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ── Name normalisation — ESPN names → our names ──
ESPN_NAME_MAP = {
    "United States":          "United States",
    "USA":                    "United States",
    "US":                     "United States",
    "Bosnia-Herzegovina":     "Bosnia and Herzegovina",
    "Bosnia & Herzegovina":   "Bosnia and Herzegovina",
    "Ivory Coast":            "Ivory Coast",
    "Cote d'Ivoire":          "Ivory Coast",
    "Côte d'Ivoire":          "Ivory Coast",
    "DR Congo":               "DR Congo",
    "Congo DR":               "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
    "Korea Republic":         "South Korea",
    "South Korea":            "South Korea",
    "Czech Republic":         "Czechia",
    "Czechia":                "Czechia",
    "Cape Verde":             "Cape Verde",
    "Cabo Verde":             "Cape Verde",
    "Cape Verde Islands":     "Cape Verde",
    "Morocco":                "Morocco",
    "Paraguay":               "Paraguay",
    "Norway":                 "Norway",
    "France":                 "France",
    "Brazil":                 "Brazil",
    "Canada":                 "Canada",
    "Germany":                "Germany",
    "Netherlands":            "Netherlands",
    "Mexico":                 "Mexico",
    "Ecuador":                "Ecuador",
    "England":                "England",
    "Belgium":                "Belgium",
    "Spain":                  "Spain",
    "Portugal":               "Portugal",
    "Argentina":              "Argentina",
    "Switzerland":            "Switzerland",
    "Algeria":                "Algeria",
    "Australia":              "Australia",
    "Egypt":                  "Egypt",
    "Colombia":               "Colombia",
    "Ghana":                  "Ghana",
    "Japan":                  "Japan",
    "South Africa":           "South Africa",
    "Austria":                "Austria",
    "Croatia":                "Croatia",
    "Senegal":                "Senegal",
}

def normalise(name):
    return ESPN_NAME_MAP.get(name, name)

# ── Verified baseline snapshot ──
# These are matches we KNOW happened with verified scores.
# ESPN API will add any we missed automatically.
VERIFIED_RESULTS = {
    ("Canada",      "South Africa"): (1, 0, "Canada",    "90min"),
    ("Brazil",      "Japan"):        (2, 1, "Brazil",    "90min"),
    ("Germany",     "Paraguay"):     (1, 1, "Paraguay",  "PKs 4-3"),
    ("Netherlands", "Morocco"):      (1, 1, "Morocco",   "PKs 3-2"),
    ("Norway",      "Ivory Coast"):  (2, 1, "Norway",    "90min"),
    ("France",      "Sweden"):       (3, 0, "France",    "90min"),
    ("Mexico",      "Ecuador"):      (2, 0, "Mexico",    "90min"),
}

# ── Model predictions for all R32 ──
MODEL_PREDICTIONS = {
    ("Canada",       "South Africa"):          "Canada",
    ("Brazil",       "Japan"):                 "Brazil",
    ("Germany",      "Paraguay"):              "Germany",      # WRONG
    ("Netherlands",  "Morocco"):               "Netherlands",  # WRONG
    ("Norway",       "Ivory Coast"):           "Ivory Coast",  # WRONG
    ("France",       "Sweden"):                "France",
    ("Mexico",       "Ecuador"):               "Mexico",
    ("England",      "DR Congo"):              "England",
    ("Belgium",      "Senegal"):               "Belgium",
    ("United States","Bosnia and Herzegovina"):"United States",
    ("Spain",        "Austria"):               "Spain",
    ("Portugal",     "Croatia"):               "Portugal",
    ("Switzerland",  "Algeria"):               "Switzerland",
    ("Australia",    "Egypt"):                 "Australia",
    ("Argentina",    "Cape Verde"):            "Argentina",
    ("Colombia",     "Ghana"):                 "Colombia",
}

# ── R32 predictions (probabilities) ──
R32_PREDICTIONS = {
    ("England",       "DR Congo"):               {"hw":94,"aw":6, "conf":94,"winner":"England"},
    ("Belgium",       "Senegal"):                {"hw":75,"aw":25,"conf":75,"winner":"Belgium"},
    ("United States", "Bosnia and Herzegovina"): {"hw":88,"aw":12,"conf":88,"winner":"United States"},
    ("Spain",         "Austria"):                {"hw":90,"aw":10,"conf":90,"winner":"Spain"},
    ("Portugal",      "Croatia"):                {"hw":65,"aw":35,"conf":65,"winner":"Portugal"},
    ("Switzerland",   "Algeria"):                {"hw":60,"aw":40,"conf":60,"winner":"Switzerland"},
    ("Australia",     "Egypt"):                  {"hw":51,"aw":49,"conf":51,"winner":"Australia"},
    ("Argentina",     "Cape Verde"):             {"hw":94,"aw":6, "conf":94,"winner":"Argentina"},
    ("Colombia",      "Ghana"):                  {"hw":87,"aw":13,"conf":87,"winner":"Colombia"},
}

# ── Injury flags ──
INJURY_FLAGS = {
    "Brazil":    {"impact":-0.08,"note":"Rodrygo (ACL), Estevao out; Neymar fit"},
    "England":   {"impact":-0.06,"note":"Reece James doubtful"},
    "Spain":     {"impact":-0.12,"note":"Nico Williams + Yeremy Pino both out"},
    "Japan":     {"impact":-0.10,"note":"Mitoma + Minamino both out"},
    "Austria":   {"impact":-0.08,"note":"Baumgartner out"},
    "Morocco":   {"impact":-0.05,"note":"Ezzalzouli out"},
    "Argentina": {"impact":-0.02,"note":"Panichelli out"},
    "Norway":    {"impact": 0.00,"note":"Haaland fit - 5 goals in tournament"},
    "Paraguay":  {"impact": 0.05,"note":"Beat Germany PKs - massive momentum"},
    "Mexico":    {"impact":-0.03,"note":"Montes suspension served"},
}

HOST_NATIONS = {"United States", "Mexico", "Canada"}

def is_neutral(home, stage):
    if stage in ("R32","R16","QF","SF","F"):
        return True
    return home not in HOST_NATIONS


def _fetch_espn_wc():
    """
    Fetch all completed WC 2026 knockout matches from ESPN API.
    Returns dict of (home, away) -> result or empty dict on failure.
    """
    results = {}
    try:
        # ESPN scoreboard API for FIFA World Cup
        url = (
            "https://site.api.espn.com/apis/site/v2/sports/soccer"
            "/FIFA.WORLD/scoreboard?limit=50"
        )
        r = requests.get(url, headers=HEADERS, timeout=8)
        r.raise_for_status()
        events = r.json().get("events", [])

        for event in events:
            status = event.get("status", {})
            stype  = status.get("type", {})

            # Only completed matches
            if not stype.get("completed", False):
                continue

            comps = event.get("competitions", [{}])[0]
            competitors = comps.get("competitors", [])
            if len(competitors) != 2:
                continue

            home_c = next((c for c in competitors if c.get("homeAway")=="home"), competitors[0])
            away_c = next((c for c in competitors if c.get("homeAway")=="away"), competitors[1])

            home_name = normalise(home_c.get("team",{}).get("displayName",""))
            away_name = normalise(away_c.get("team",{}).get("displayName",""))

            try:
                hs = int(home_c.get("score","0") or 0)
                as_ = int(away_c.get("score","0") or 0)
            except (ValueError, TypeError):
                continue

            # Detect method (PKs / AET)
            notes   = comps.get("notes", [])
            method  = "90min"
            for n in notes:
                headline = n.get("headline", "").lower()
                if "penalt" in headline or "penalty" in headline or "pk" in headline:
                    method = "PKs"
                    break
                if "extra" in headline or "aet" in headline or "overtime" in headline:
                    method = "AET"
                    break

            # Determine winner (score or explicitly flagged)
            if hs > as_:
                winner = home_name
            elif as_ > hs:
                winner = away_name
            else:
                # Draw after 90 — look for winner note
                winner = home_name  # default; override if PKs noted
                for comp in competitors:
                    if comp.get("winner", False):
                        winner = normalise(comp.get("team",{}).get("displayName",""))
                        break

            results[(home_name, away_name)] = {
                "home":       home_name,
                "away":       away_name,
                "home_score": hs,
                "away_score": as_,
                "winner":     winner,
                "method":     method,
                "source":     "espn_api",
            }

    except Exception as exc:
        # Silently fail — caller falls back to snapshot
        pass

    return results


def _fetch_wikipedia_r32():
    """
    Secondary scraper: Wikipedia 2026 WC knockout stage page.
    Parses score tables using simple regex — fragile but free.
    Returns dict of (home, away) -> result or empty dict on failure.
    """
    results = {}
    try:
        url = (
            "https://en.wikipedia.org/wiki/"
            "2026_FIFA_World_Cup_knockout_stage"
        )
        r = requests.get(url, headers=HEADERS, timeout=8)
        r.raise_for_status()
        text = r.text

        # Match patterns like:  Brazil 2–1 Japan  or  Paraguay 1–1 (a.e.t.) Germany
        # Wikipedia uses en-dash (–) in scores
        pattern = re.compile(
            r'([A-Z][a-zA-Z\s]+?)\s+'     # team A
            r'(\d+)\s*[–\-]\s*(\d+)'      # score
            r'(?:\s*\(.*?\))?\s+'          # optional (a.e.t.) / (p.)
            r'([A-Z][a-zA-Z\s]+?)(?:\n|<)', # team B
            re.MULTILINE
        )
        for m in pattern.finditer(text):
            home  = normalise(m.group(1).strip())
            hs    = int(m.group(2))
            as_   = int(m.group(3))
            away  = normalise(m.group(4).strip())
            if home and away and home != away:
                winner = home if hs > as_ else away
                results[(home, away)] = {
                    "home": home, "away": away,
                    "home_score": hs, "away_score": as_,
                    "winner": winner, "method": "90min",
                    "source": "wikipedia",
                }
    except Exception:
        pass
    return results


def get_live_data(force_refresh=False):
    """
    Returns fully up-to-date WC data.
    Priority:
      1. Fresh cache (< 15 min)
      2. ESPN API
      3. Wikipedia scrape
      4. Verified snapshot
    All sources merged — ESPN + Wikipedia supplement the snapshot.
    """
    # 1. Cache
    if not force_refresh and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            age   = datetime.datetime.now().timestamp() - cache.get("ts", 0)
            if age < CACHE_TTL:
                return cache["data"]
        except Exception:
            pass

    # 2. Start from verified snapshot
    confirmed = {}
    for (home, away), (hs, as_, winner, method) in VERIFIED_RESULTS.items():
        confirmed[(home, away)] = {
            "home": home, "away": away,
            "home_score": hs, "away_score": as_,
            "winner": winner, "method": method,
            "source": "snapshot",
            "model_correct": MODEL_PREDICTIONS.get(
                (home, away), MODEL_PREDICTIONS.get((away, home))
            ) == winner,
        }

    api_source = "verified snapshot"

    # 3. Try ESPN API
    espn = _fetch_espn_wc()
    if espn:
        for key, result in espn.items():
            home, away = key
            # Add model_correct flag
            pred = MODEL_PREDICTIONS.get((home, away),
                   MODEL_PREDICTIONS.get((away, home)))
            result["model_correct"] = (pred == result["winner"])
            confirmed[key] = result
        api_source = "ESPN API + snapshot"

    # 4. Try Wikipedia as supplement
    if len(confirmed) < 7:   # only if ESPN missed things
        wiki = _fetch_wikipedia_r32()
        for key, result in wiki.items():
            if key not in confirmed:
                pred = MODEL_PREDICTIONS.get(key,
                       MODEL_PREDICTIONS.get((key[1], key[0])))
                result["model_correct"] = (pred == result["winner"])
                confirmed[key] = result
        if wiki:
            api_source += " + Wikipedia"

    # Build upsets list dynamically
    upsets = []
    for (home, away), res in confirmed.items():
        pred = MODEL_PREDICTIONS.get((home, away),
               MODEL_PREDICTIONS.get((away, home)))
        if pred and pred != res["winner"]:
            severity = "historic" if res["method"] == "PKs" else "major"
            upsets.append({
                "match":    f"{home} vs {away}",
                "result":   f"{res['winner']} advanced ({res['method']})",
                "date":     "R32",
                "severity": severity,
            })

    # Model accuracy
    total   = len(confirmed)
    correct = sum(1 for v in confirmed.values() if v.get("model_correct", False))

    data = {
        "confirmed_r32":    {str(k): v for k, v in confirmed.items()},
        "confirmed_r32_raw": confirmed,
        "r32_predictions":  R32_PREDICTIONS,
        "injury_flags":     INJURY_FLAGS,
        "upsets":           upsets,
        "last_updated":     datetime.datetime.now().strftime("%b %d %H:%M ET"),
        "r32_complete":     total,
        "r32_total":        16,
        "model_correct":    correct,
        "model_total":      total,
        "data_source":      api_source,
    }

    # Cache
    try:
        CACHE_FILE.write_text(
            json.dumps({"ts": datetime.datetime.now().timestamp(),
                        "data": data}, default=str),
            encoding="utf-8"
        )
    except Exception:
        pass

    return data


def model_accuracy_r32(data):
    return data.get("model_correct", 0), data.get("model_total", 0)


if __name__ == "__main__":
    import sys
    force = "--refresh" in sys.argv
    data  = get_live_data(force_refresh=force)
    print(f"Source:   {data['data_source']}")
    print(f"Updated:  {data['last_updated']}")
    print(f"R32 done: {data['r32_complete']}/{data['r32_total']}")
    c, t = model_accuracy_r32(data)
    print(f"Accuracy: {c}/{t} ({int(c/t*100) if t else 0}%) on completed R32")
    print(f"Upsets:   {[u['match']+': '+u['result'] for u in data['upsets']]}")
