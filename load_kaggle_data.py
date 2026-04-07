"""
load_kaggle_data.py  —  ETL: Kaggle FIFA CSV files → fifa.db
=============================================================
Authors : Veda Abhishek Kovvireddy  — WorldCups.csv loader, countries/tournaments
          Jyothi Swaroop Malladi    — WorldCupMatches.csv loader, venues/matches
          Mohammed Aazam Tadipatri  — WorldCupPlayers.csv loader, players/stats/events

Course  : Applied Database Design — IU Bloomington
Dataset : https://www.kaggle.com/datasets/abecklas/fifa-world-cup
          Three CSV files: WorldCups.csv, WorldCupMatches.csv, WorldCupPlayers.csv

Usage:
    1. Download the Kaggle dataset and place the 3 CSV files in:
           fifa_worldcup/data/
    2. Run:  python load_kaggle_data.py
    3. Then: python app.py

This script REPLACES the hardcoded seed data in schema.sql with real data.
It rebuilds fifa.db from scratch on every run.

AI Assistance: ETL structure reviewed with Claude (Anthropic, claude-sonnet-4-20250514),
               accessed April 2026.
Reference    : https://www.kaggle.com/datasets/abecklas/fifa-world-cup
"""

import sqlite3
import os
import re
import datetime
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join(BASE_DIR, "fifa.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
DATA_DIR    = os.path.join(BASE_DIR, "data")

CSV_CUPS    = os.path.join(DATA_DIR, "WorldCups.csv")
CSV_MATCHES = os.path.join(DATA_DIR, "WorldCupMatches.csv")
CSV_PLAYERS = os.path.join(DATA_DIR, "WorldCupPlayers.csv")


# ══════════════════════════════════════════════════════════════════════════════
# NORMALIZATION TABLES
# Author: Veda Abhishek Kovvireddy
# The Kaggle CSVs use inconsistent/historical country names.
# We map them to the canonical names used in our schema.
# ══════════════════════════════════════════════════════════════════════════════
NAME_MAP = {
    # Historical West Germany
    "Germany FR":                       "West Germany",
    "FR Germany":                       "West Germany",
    # Korea
    "Korea Republic":                   "South Korea",
    "Korea DPR":                        "North Korea",
    # Iran
    "IR Iran":                          "Iran",
    # Ivory Coast — multiple encodings exist in the CSV
    "C?te d'Ivoire":                    "Ivory Coast",
    "Cote d'Ivoire":                    "Ivory Coast",
    "Côte d'Ivoire":                    "Ivory Coast",
    "rn\">Côte d'Ivoire":               "Ivory Coast",
    "rn\">rn\">Côte d'Ivoire":          "Ivory Coast",
    # USA
    "USA":                              "United States",
    # Former states
    "Serbia and Montenegro":            "Serbia",
    "Federal Republic of Yugoslavia":   "Yugoslavia",
    "Trinidad and Tobago":              "Trinidad & Tobago",
    "Bosnia and Herzegovina":           "Bosnia & Herzegovina",
    "China PR":                         "China",
    "Dutch East Indies":                "Dutch East Indies",   # keep historic name
    "Republic of Ireland":              "Ireland",
    "Northern Ireland":                 "Northern Ireland",
    "Zaire":                            "Zaire",
    "Soviet Union":                     "Soviet Union",
}

def normalize(name: str) -> str | None:
    """
    Return canonical country name, or None if the value is blank/NaN.
    Author: Veda Abhishek Kovvireddy
    """
    if not isinstance(name, str):
        return None
    name = name.strip()
    if name.lower() in ("nan", "none", ""):
        return None
    return NAME_MAP.get(name, name)


# Confederation lookup
# Author: Veda Abhishek Kovvireddy
CONFED = {
    "Brazil":"CONMEBOL","Argentina":"CONMEBOL","Uruguay":"CONMEBOL","Chile":"CONMEBOL",
    "Colombia":"CONMEBOL","Paraguay":"CONMEBOL","Peru":"CONMEBOL","Ecuador":"CONMEBOL",
    "Bolivia":"CONMEBOL","Venezuela":"CONMEBOL",
    "Germany":"UEFA","West Germany":"UEFA","Italy":"UEFA","France":"UEFA",
    "Spain":"UEFA","England":"UEFA","Netherlands":"UEFA","Portugal":"UEFA",
    "Belgium":"UEFA","Croatia":"UEFA","Sweden":"UEFA","Hungary":"UEFA",
    "Czechoslovakia":"UEFA","Yugoslavia":"UEFA","Poland":"UEFA","Romania":"UEFA",
    "Denmark":"UEFA","Switzerland":"UEFA","Austria":"UEFA","Scotland":"UEFA",
    "Bulgaria":"UEFA","Greece":"UEFA","Turkey":"UEFA","Russia":"UEFA",
    "Soviet Union":"UEFA","Serbia":"UEFA","Ukraine":"UEFA","Czech Republic":"UEFA",
    "Slovakia":"UEFA","Slovenia":"UEFA","Bosnia & Herzegovina":"UEFA","Iceland":"UEFA",
    "Ireland":"UEFA","Northern Ireland":"UEFA","Wales":"UEFA","Norway":"UEFA",
    "Finland":"UEFA","Albania":"UEFA","North Macedonia":"UEFA","Kosovo":"UEFA",
    "Montenegro":"UEFA","Luxembourg":"UEFA","Malta":"UEFA","Cyprus":"UEFA",
    "San Marino":"UEFA","Andorra":"UEFA","Liechtenstein":"UEFA",
    "United States":"CONCACAF","Mexico":"CONCACAF","Costa Rica":"CONCACAF",
    "Honduras":"CONCACAF","Cuba":"CONCACAF","El Salvador":"CONCACAF",
    "Haiti":"CONCACAF","Jamaica":"CONCACAF","Trinidad & Tobago":"CONCACAF",
    "Canada":"CONCACAF","Panama":"CONCACAF",
    "Morocco":"CAF","Senegal":"CAF","Cameroon":"CAF","Nigeria":"CAF",
    "Egypt":"CAF","Zaire":"CAF","Tunisia":"CAF","Algeria":"CAF",
    "Ivory Coast":"CAF","Ghana":"CAF","Angola":"CAF","Togo":"CAF",
    "South Africa":"CAF","Zambia":"CAF","DR Congo":"CAF",
    "South Korea":"AFC","Japan":"AFC","Australia":"AFC","Iran":"AFC",
    "Saudi Arabia":"AFC","North Korea":"AFC","China":"AFC","Iraq":"AFC",
    "Kuwait":"AFC","Qatar":"AFC","Dutch East Indies":"AFC","UAE":"AFC",
    "Indonesia":"AFC","Uzbekistan":"AFC","Bahrain":"AFC",
    "New Zealand":"OFC",
}

# Stage → round_num mapping
# Author: Jyothi Swaroop Malladi
ROUND_MAP = {
    "group stage":1, "group stage a":1, "group stage b":1, "group stage c":1,
    "group stage d":1, "group stage e":1, "group stage f":1, "group stage g":1,
    "group stage h":1, "first round":1, "preliminary round":1,
    "second round":2, "round of 16":2,
    "quarter-finals":3, "quarter finals":3, "quarterfinals":3,
    "semi-finals":4,   "semi finals":4,   "semifinals":4,
    "third place":5,   "third-place play-off":5, "play-off for third place":5,
    "place 3":5,       "third place play-off":5,
    "final":6,
}

def get_round(stage: str) -> int | None:
    """Author: Jyothi Swaroop Malladi"""
    if not isinstance(stage, str):
        return None
    return ROUND_MAP.get(stage.strip().lower())


# ══════════════════════════════════════════════════════════════════════════════
# DB HELPERS
# Author: Veda Abhishek Kovvireddy
# ══════════════════════════════════════════════════════════════════════════════
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Apply schema DDL (creates all tables + views, no seed data)
# Author: Veda Abhishek Kovvireddy
# ══════════════════════════════════════════════════════════════════════════════

def apply_schema(conn):
    """
    Reads schema.sql but strips out the INSERT/DML section so only the
    table/view DDL is applied. We load our own data from the CSVs instead.
    Author: Veda Abhishek Kovvireddy
    """
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        raw = f.read()

    # Keep everything EXCEPT the DML seed data block
    # Split into 3 parts: DDL | Seed Data | Views
    parts = raw.split("-- DML — Seed Data")
    ddl = parts[0]  # tables only

    # Get the views section (after the seed data)
    views = ""
    if len(parts) > 1:
        view_split = parts[1].split("-- VIEWS —")
        if len(view_split) > 1:
            views = "-- VIEWS —" + view_split[1]

    conn.executescript(ddl + views)
    conn.commit()
    print("  [✓] Schema DDL applied (tables + views created)")
# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Load WorldCups.csv → countries + tournaments
# Author: Veda Abhishek Kovvireddy
# CSV columns: Year, Country, Winner, Runners-Up, Third, Fourth,
#              GoalsScored, QualifiedTeams, MatchesPlayed, Attendance
# ══════════════════════════════════════════════════════════════════════════════
def load_worldcups(conn) -> set:
    """
    Populates `countries` and `tournaments` tables from WorldCups.csv.
    Returns the set of canonical country names already inserted.
    Author: Veda Abhishek Kovvireddy
    """
    df = pd.read_csv(CSV_CUPS)
    df.columns = df.columns.str.strip()
    print(f"  WorldCups.csv  →  {len(df)} rows  |  columns: {list(df.columns)}")

    cur = conn.cursor()
    c_seen = set()  # tracks names already inserted into countries

    def clean_int(v) -> int | None:
        """Parse integers that may contain commas, spaces, or decimals."""
        try:
            return int(str(v).replace(",", "").replace(" ", "").split(".")[0])
        except Exception:
            return None

    def upsert_country(raw_name: str) -> None:
        """Insert country if not already present. Author: Veda Abhishek Kovvireddy"""
        name = normalize(raw_name)
        if not name or name in c_seen:
            return
        cur.execute(
            "INSERT OR IGNORE INTO countries(name, confederation) VALUES (?,?)",
            (name, CONFED.get(name)),
        )
        c_seen.add(name)

    t_count = 0
    for _, row in df.iterrows():
        year       = clean_int(row["Year"])
        host       = normalize(str(row.get("Country", "")))
        winner     = normalize(str(row.get("Winner", "")))
        runner_up  = normalize(str(row.get("Runners-Up", "")))
        third      = normalize(str(row.get("Third", "")))
        goals      = clean_int(row.get("GoalsScored"))
        matches    = clean_int(row.get("MatchesPlayed"))
        attendance = clean_int(row.get("Attendance"))

        if not year:
            continue

        # Register every country mentioned in this row
        for n in [host, winner, runner_up, third,
                  normalize(str(row.get("Fourth", "")))]:
            upsert_country(n or "")

        cur.execute("""
            INSERT OR IGNORE INTO tournaments
                (year, host_country, winner, runner_up, third_place,
                 total_goals, total_matches, total_attendance)
            VALUES (?,?,?,?,?,?,?,?)
        """, (year, host, winner, runner_up, third,
              goals, matches, attendance))
        t_count += 1

    conn.commit()
    print(f"  [✓] {t_count} tournaments  |  {len(c_seen)} countries inserted")
    return c_seen


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Load WorldCupMatches.csv → venues + matches
# Author: Jyothi Swaroop Malladi
# CSV columns: Year, Datetime, Stage, Stadium, City,
#   Home Team Name, Home Team Goals, Away Team Goals, Away Team Name,
#   Win Conditions, Attendance, Half-time Home Goals, Half-time Away Goals,
#   Referee, Assistant 1, Assistant 2, RoundID, MatchID,
#   Home Team Initials, Away Team Initials
# ══════════════════════════════════════════════════════════════════════════════
def load_matches(conn, c_seen: set) -> dict:
    """
    Populates `venues` and `matches` tables from WorldCupMatches.csv.
    Returns a dict: csv MatchID → internal match_id (for event linkage).
    Author: Jyothi Swaroop Malladi
    """
    df = pd.read_csv(CSV_MATCHES, encoding="utf-8", on_bad_lines="skip")
    df.columns = df.columns.str.strip()
    print(f"  WorldCupMatches.csv  →  {len(df)} rows (raw)  |  columns: {list(df.columns)}")

    # Step 1: Drop entirely blank rows
    df = df.dropna(subset=["Home Team Name", "Away Team Name"])
    # Step 2: Deduplicate by MatchID — Kaggle CSV contains ~3,700 duplicate rows
    # where the same match appears multiple times with identical MatchID.
    # keep="first" retains the first occurrence and discards all duplicates.
    # This MUST happen before any DB inserts to prevent duplicate match records.
    # Author: Jyothi Swaroop Malladi
    if "MatchID" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["MatchID"], keep="first")
        dropped = before - len(df)
        if dropped:
            print(f"  [!] Dropped {dropped} duplicate MatchID rows from CSV")
    print(f"  WorldCupMatches.csv  →  {len(df)} rows (after dedup)")

    cur = conn.cursor()

    # ── Register any new countries that appear only in matches CSV ────────────
    # Author: Jyothi Swaroop Malladi
    for col in ["Home Team Name", "Away Team Name"]:
        for raw in df[col].dropna().unique():
            name = normalize(str(raw))
            if name and name not in c_seen:
                cur.execute(
                    "INSERT OR IGNORE INTO countries(name, confederation) VALUES (?,?)",
                    (name, CONFED.get(name)),
                )
                c_seen.add(name)
    conn.commit()

    # ── Build venue cache: (Stadium, City) → venue_id ────────────────────────
    # Author: Jyothi Swaroop Malladi
    venue_cache: dict[tuple, int | None] = {}
    for _, row in df.iterrows():
        stadium = str(row.get("Stadium", "")).strip()
        city    = str(row.get("City", "")).strip()
        if not stadium or stadium.lower() == "nan":
            continue
        key = (stadium, city)
        if key in venue_cache:
            continue
        # Get host country from tournament year for venue.country field
        year = int(float(row["Year"])) if pd.notna(row.get("Year")) else None
        host = ""
        if year:
            t_row = cur.execute(
                "SELECT host_country FROM tournaments WHERE year=?", (year,)
            ).fetchone()
            host = t_row[0] if t_row else ""
        cur.execute(
            "INSERT OR IGNORE INTO venues(name, city, country) VALUES (?,?,?)",
            (stadium, city, host),
        )
        v = cur.execute(
            "SELECT venue_id FROM venues WHERE name=? AND city=?", (stadium, city)
        ).fetchone()
        venue_cache[key] = v[0] if v else None
    conn.commit()
    print(f"  [✓] {len(venue_cache)} venues inserted")

    # ── Date parser ──────────────────────────────────────────────────────────
    def parse_date(raw) -> str | None:
        """
        Handles formats like '13 Jul 1930 - 15:00' and '1930-07-13'.
        Author: Jyothi Swaroop Malladi
        """
        if not isinstance(raw, str):
            return None
        m = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", raw)
        if m:
            try:
                return datetime.datetime.strptime(m.group(1), "%d %b %Y").strftime("%Y-%m-%d")
            except Exception:
                pass
        m2 = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
        return m2.group(1) if m2 else None

    def safe_int(v, default=0) -> int:
        try:
            return int(float(v))
        except Exception:
            return default

    # ── Insert matches ────────────────────────────────────────────────────────
    # Author: Jyothi Swaroop Malladi
    match_id_map: dict[int, int] = {}   # csv MatchID → our match_id
    inserted = 0
    skipped  = 0

    for _, row in df.iterrows():
        try:
            year      = int(float(row["Year"]))
            home_name = normalize(str(row["Home Team Name"]))
            away_name = normalize(str(row["Away Team Name"]))
            stage     = str(row.get("Stage", "")).strip()

            # Look up FK IDs
            t_row = cur.execute(
                "SELECT tournament_id FROM tournaments WHERE year=?", (year,)
            ).fetchone()
            h_row = cur.execute(
                "SELECT country_id FROM countries WHERE name=?", (home_name,)
            ).fetchone()
            a_row = cur.execute(
                "SELECT country_id FROM countries WHERE name=?", (away_name,)
            ).fetchone()

            if not (t_row and h_row and a_row):
                skipped += 1
                continue

            stadium = str(row.get("Stadium", "")).strip()
            city    = str(row.get("City", "")).strip()
            vid     = venue_cache.get((stadium, city))

            cur.execute("""
                INSERT INTO matches
                    (tournament_id, venue_id, home_team_id, away_team_id,
                     home_score, away_score, stage, round_num,
                     match_date, attendance)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                t_row[0], vid, h_row[0], a_row[0],
                safe_int(row.get("Home Team Goals", 0)),
                safe_int(row.get("Away Team Goals", 0)),
                stage,
                get_round(stage),
                parse_date(str(row.get("Datetime", ""))),
                safe_int(row.get("Attendance")) or None,
            ))

            our_match_id = cur.lastrowid
            inserted += 1

            # Map CSV MatchID → our match_id for event linkage
            csv_mid = row.get("MatchID")
            if pd.notna(csv_mid):
                match_id_map[int(float(csv_mid))] = our_match_id

        except Exception:
            skipped += 1

    conn.commit()
    print(f"  [✓] {inserted} matches inserted  |  {skipped} skipped")
    return match_id_map


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Load WorldCupPlayers.csv → players + player_stats + events
# Author: Mohammed Aazam Tadipatri
# CSV columns: RoundID, MatchID, Team Initials, Coach Name, Line-up,
#              Shirt Number, Player Name, Position, Event
#
# Event column encoding:
#   G  = Goal          OG = Own Goal     P/PG = Penalty Goal
#   Y  = Yellow Card   R  = Red Card     Y2R  = 2nd Yellow → Red
# Format examples: "G23' G67'"  "Y55'"  "OG12'"  "P(pen)90'"
# ══════════════════════════════════════════════════════════════════════════════
def parse_event_type(code: str) -> str:
    c = code.strip().upper()

    if c.startswith("OG"):
        return "own_goal"
    if c.startswith("PG") or c.startswith("P("):
        return "penalty_goal"
    if c.startswith("G"):
        return "goal"
    if c.startswith("Y2R"):
        return "red_card"   # ✅ FIXED
    if c.startswith("Y"):
        return "yellow_card"
    if c.startswith("R"):
        return "red_card"

    return "goal"  # safe fallback


def load_players(conn, match_id_map: dict) -> None:
    """
    Populates `players`, `player_stats`, and `events` tables from WorldCupPlayers.csv.

    Key fixes applied (Mohammed Aazam Tadipatri):
      FIX 1 — Tournament ID resolution: The original code tried to extract the year
               from RoundID using [:4] slicing, but Kaggle RoundIDs are sequential
               integers (e.g. 201497), NOT year-prefixed. The correct approach is to
               resolve tournament_id via MatchID → match_id_map → matches table, which
               already carries the correct tournament_id FK.
      FIX 2 — Country resolution: Team Initials (e.g. "BRA") are used to look up the
               country_id so players are linked to their nation.
      FIX 3 — Position: The CSV 'Position' column is now stored on the player row.
      FIX 4 — Event type: Events are parsed into typed strings (goal, yellow_card, etc.)
               instead of the generic fallback "event".
    Author: Mohammed Aazam Tadipatri
    """
    df = pd.read_csv(CSV_PLAYERS, encoding="utf-8", on_bad_lines="skip")
    df.columns = df.columns.str.strip()

    print(f"  WorldCupPlayers.csv → {len(df)} rows")

    cur = conn.cursor()

    # ── Pre-build a lookup: team_initials → country_id ───────────────────────
    # WorldCupMatches.csv has both 'Home Team Name' and 'Home Team Initials',
    # so we can reconstruct the mapping from the matches table joined to countries.
    # Author: Mohammed Aazam Tadipatri
    initials_to_cid: dict[str, int] = {}
    matches_df = pd.read_csv(CSV_MATCHES, encoding="utf-8", on_bad_lines="skip")
    matches_df.columns = matches_df.columns.str.strip()
    for _, mrow in matches_df.iterrows():
        for side in [("Home Team Name", "Home Team Initials"),
                     ("Away Team Name", "Away Team Initials")]:
            name_col, ini_col = side
            raw_name = str(mrow.get(name_col, "")).strip()
            raw_ini  = str(mrow.get(ini_col, "")).strip().upper()
            if not raw_ini or raw_ini in ("NAN", ""):
                continue
            canon = normalize(raw_name)
            if not canon:
                continue
            if raw_ini not in initials_to_cid:
                c_row = cur.execute(
                    "SELECT country_id FROM countries WHERE name=?", (canon,)
                ).fetchone()
                if c_row:
                    initials_to_cid[raw_ini] = c_row[0]

    # ── Pre-build a lookup: our match_id → tournament_id ────────────────────
    # FIX 1: This avoids the broken RoundID[:4] year-extraction logic.
    # Author: Mohammed Aazam Tadipatri
    mid_to_tid: dict[int, int] = {}
    for csv_mid, our_mid in match_id_map.items():
        t_row = cur.execute(
            "SELECT tournament_id FROM matches WHERE match_id=?", (our_mid,)
        ).fetchone()
        if t_row:
            mid_to_tid[our_mid] = t_row[0]

    player_cache: dict[tuple, int | None] = {}
    stats_acc: dict[tuple, dict] = {}
    events_buf: list[tuple] = []

    processed = skipped = 0

    for _, row in df.iterrows():
        try:
            pname     = str(row.get("Player Name", "")).strip()
            team_ini  = str(row.get("Team Initials", "")).strip().upper()
            position  = str(row.get("Position", "")).strip() or None
            match_id_csv = row.get("MatchID")

            if not pname or pname.lower() in ("nan", ""):
                continue

            # ── Resolve our internal match_id and tournament_id ──────────────
            # FIX 1: use match_id_map (csv MatchID → our match_id) then look up
            #        tournament_id from the matches table.  No RoundID[:4] slicing.
            csv_mid = int(float(match_id_csv)) if pd.notna(match_id_csv) else None
            our_mid = match_id_map.get(csv_mid)
            tid     = mid_to_tid.get(our_mid) if our_mid else None

            if not tid:
                skipped += 1
                continue

            # ── Resolve country_id via team initials (FIX 2) ─────────────────
            cid = initials_to_cid.get(team_ini)   # None is acceptable

            # ── Insert / cache player ────────────────────────────────────────
            # Cache key includes position so the same player in different roles
            # is treated as one person (name+cid uniquely identifies a player).
            pk = (pname, cid)

            if pk not in player_cache:
                cur.execute(
                    "INSERT OR IGNORE INTO players(name, country_id, position) VALUES (?,?,?)",
                    (pname, cid, position),   # FIX 3: store position
                )
                pid_row = cur.execute(
                    "SELECT player_id FROM players WHERE name=? AND country_id IS ?",
                    (pname, cid),
                ).fetchone()
                player_cache[pk] = pid_row[0] if pid_row else None

            pid = player_cache.get(pk)
            if not pid:
                continue

            # ── Accumulate player_stats ──────────────────────────────────────
            sk = (pid, tid)
            if sk not in stats_acc:
                stats_acc[sk] = {"goals": 0, "apps": 0}
            stats_acc[sk]["apps"] += 1

            # ── Parse and buffer events ──────────────────────────────────────
            # FIX 4: parse each individual event token instead of storing "event".
            # Format examples: "G23' G67'"  "Y55'"  "OG12'"  "P(pen)90'"
            # Author: Mohammed Aazam Tadipatri
            event_str = str(row.get("Event", "")).strip()
            if event_str and event_str.lower() not in ("nan", "") and our_mid:
                # Split on whitespace to handle multiple events per row
                for token in event_str.split():
                    token = token.strip("'").strip()
                    if not token:
                        continue
                    minutes_found = re.findall(r"\d+", token)
                    minute = int(minutes_found[0]) if minutes_found else 0
                    etype  = parse_event_type(token)
                    events_buf.append((our_mid, pid, etype, minute, cid))
                    if etype in ("goal", "penalty_goal", "own_goal"):
                        stats_acc[sk]["goals"] += 1

            processed += 1

        except Exception:
            skipped += 1

    # ── Bulk-insert player_stats ─────────────────────────────────────────────
    for (pid, tid), vals in stats_acc.items():
        cur.execute("""
            INSERT OR IGNORE INTO player_stats
            (player_id, tournament_id, goals, matches_played)
            VALUES (?,?,?,?)
        """, (pid, tid, vals["goals"], vals["apps"]))

    # ── Bulk-insert events ───────────────────────────────────────────────────
    for (mid, pid, etype, minute, team_id) in events_buf:
        cur.execute("""
            INSERT INTO events(match_id, player_id, event_type, minute, team_id)
            VALUES (?,?,?,?,?)
        """, (mid, pid, etype, minute, team_id))

    conn.commit()

    print(f"  [✓] players loaded: {len(player_cache)}")
    print(f"  [✓] stats: {len(stats_acc)}")
    print(f"  [✓] events: {len(events_buf)}")
    print(f"      ({processed} processed | {skipped} skipped)")
    
# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# Author: Veda Abhishek Kovvireddy
# ══════════════════════════════════════════════════════════════════════════════
def print_summary(conn) -> None:
    print(f"\n{'='*60}")
    print("  FIFA World Cup Database — final row counts")
    print(f"{'='*60}")
    for tbl in ["countries", "tournaments", "venues", "matches",
                "players", "player_stats", "events", "audit_log"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:<20}  {n:>7,} rows")
    print(f"\n  Database: {DB_PATH}")
    print(f"{'='*60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # ── Pre-flight: verify CSV files exist ───────────────────────────────────
    missing = [f for f in [CSV_CUPS, CSV_MATCHES, CSV_PLAYERS] if not os.path.exists(f)]
    if missing:
        print("\n" + "="*60)
        print("  ERROR — Kaggle CSV files not found!")
        print("="*60)
        print(f"  Expected location:  {DATA_DIR}/\n")
        for fname in ["WorldCups.csv", "WorldCupMatches.csv", "WorldCupPlayers.csv"]:
            full = os.path.join(DATA_DIR, fname)
            tag  = "✓ found" if os.path.exists(full) else "✗ MISSING"
            print(f"    {tag}  →  {fname}")
        print("\n  Download from: https://www.kaggle.com/datasets/abecklas/fifa-world-cup")
        print("  Then place the 3 CSV files in the  data/  folder.\n")
        return

    # ── Drop existing DB for clean rebuild ───────────────────────────────────
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"[!] Removed existing {os.path.basename(DB_PATH)} — rebuilding from Kaggle data")

    print(f"\n{'='*60}")
    print("  FIFA World Cup Database — ETL from Kaggle CSVs")
    print(f"{'='*60}\n")

    conn = get_conn()
    try:
        print("[1/5] Applying DDL schema (tables + views)...")
        apply_schema(conn)

        print("[2/5] Loading WorldCups.csv  →  countries + tournaments...")
        c_seen = load_worldcups(conn)

        print("[3/5] Loading WorldCupMatches.csv  →  venues + matches...")
        match_id_map = load_matches(conn, c_seen)

        print("[4/5] Loading WorldCupPlayers.csv  →  players + stats + events...")
        load_players(conn, match_id_map)

        print("[5/5] Summary:")
        print_summary(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
