"""
app.py — FIFA World Cup Historical Performance Database
Flask web application with full CRUD + analytics
Authors: Veda Abhishek Kovvireddy, Jyothi Swaroop Malladi, Mohammed Aazam Tadipatri
AI Assistance: Route logic reviewed with Claude (Anthropic), accessed April 2026.
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from db import get_connection, init_db
import os, json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fifa_wc_secret_2026")

# ─────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────
@app.before_request
def ensure_db():
    if not os.path.exists("fifa.db"):
        init_db()


# ─────────────────────────────────────────────
# HOME / DASHBOARD /
# Author: Veda Abhishek Kovvireddy
# ─────────────────────────────────────────────
@app.route("/")
def index():
    conn = get_connection()
    stats = {}
    stats["tournaments"] = conn.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0]
    stats["matches"]     = conn.execute("SELECT COUNT(*) FROM matches WHERE is_deleted=0").fetchone()[0]
    stats["countries"]   = conn.execute("SELECT COUNT(*) FROM countries").fetchone()[0]
    stats["players"]     = conn.execute("SELECT COUNT(*) FROM players WHERE is_deleted=0").fetchone()[0]
    stats["total_goals"] = conn.execute("SELECT SUM(total_goals) FROM tournaments").fetchone()[0] or 0

    recent_matches = conn.execute("""
        SELECT vm.year, vm.home_team, vm.away_team, vm.home_score,
               vm.away_score, vm.stage, vm.match_date
        FROM vw_matches vm
        ORDER BY vm.year DESC, vm.round_num DESC
        LIMIT 8
    """).fetchall()

    winners = conn.execute("SELECT * FROM vw_country_wins LIMIT 10").fetchall()
    conn.close()
    return render_template("index.html", stats=stats,
                           recent_matches=recent_matches, winners=winners)


# ─────────────────────────────────────────────
# TOURNAMENTS — READ
# ─────────────────────────────────────────────
@app.route("/tournaments")
def tournaments():
    """
    Read all tournament editions with full podium data.
    Queries tournaments table directly (not vw_goals_per_tournament view)
    so runner_up and third_place are available.
    Contributor: Veda Abhishek Kovvireddy
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT year, host_country, winner, runner_up, third_place,
               total_goals, total_matches, total_attendance,
               ROUND(CAST(total_goals AS REAL) / NULLIF(total_matches, 0), 2) AS avg_goals_per_match
        FROM tournaments
        ORDER BY year DESC
    """).fetchall()
    conn.close()
    return render_template("tournaments.html", tournaments=rows)


# ─────────────────────────────────────────────
# MATCHES — READ / CREATE / UPDATE / DELETE
# Author - Veda Abhishek Kovvireddy
# ─────────────────────────────────────────────
@app.route("/matches")
def matches():
    year    = request.args.get("year", "")
    team    = request.args.get("team", "")
    stage   = request.args.get("stage", "")
    conn    = get_connection()

    # Deduplicate by match_id to guard against duplicate rows that can arise
    # when the Kaggle CSV has repeated MatchID entries loaded into the DB.
    # GROUP BY match_id is the safest guarantee of one row per match.
    # Contributor: Jyothi Swaroop Malladi
    query = """
        SELECT match_id, year, stage, round_num, match_date,
               home_team, away_team, home_score, away_score,
               attendance, venue, city
        FROM vw_matches WHERE 1=1
    """
    params = []
    if year:
        query += " AND year=?"; params.append(year)
    if team:
        query += " AND (home_team LIKE ? OR away_team LIKE ?)"; params += [f"%{team}%", f"%{team}%"]
    if stage:
        query += " AND stage=?"; params.append(stage)
    query += " GROUP BY match_id ORDER BY year DESC, round_num DESC"

    rows        = conn.execute(query, params).fetchall()
    years       = [r[0] for r in conn.execute("SELECT DISTINCT year FROM tournaments ORDER BY year DESC").fetchall()]
    stages      = [r[0] for r in conn.execute("SELECT DISTINCT stage FROM matches WHERE is_deleted=0 ORDER BY stage").fetchall()]
    countries   = conn.execute("SELECT country_id, name FROM countries ORDER BY name").fetchall()
    tournaments = conn.execute("SELECT tournament_id, year FROM tournaments ORDER BY year DESC").fetchall()
    venues      = conn.execute("SELECT venue_id, name, city FROM venues ORDER BY name").fetchall()
    conn.close()
    return render_template("matches.html", matches=rows, years=years,
                           stages=stages, countries=countries,
                           tournaments=tournaments, venues=venues,
                           filters={"year": year, "team": team, "stage": stage})


@app.route("/tournaments/add", methods=["POST"])
def add_tournament():
    """CREATE — add a new tournament year so matches can be added for it."""
    d = request.form
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO tournaments(year, host_country, winner, runner_up, third_place,
                                              total_goals, total_matches, total_attendance)
            VALUES (?,?,?,?,?,0,0,0)
        """, (d["year"], d.get("host_country") or "TBD",
              d.get("winner") or None, d.get("runner_up") or None, d.get("third_place") or None))
        conn.execute("INSERT INTO audit_log(table_name,record_id,action,details) VALUES('tournaments',last_insert_rowid(),'INSERT',?)",
                     (json.dumps(dict(d)),))
        conn.commit()
        flash(f"✅ Tournament {d['year']} added!", "success")
    except Exception as e:
        flash(f"❌ Error: {e}", "danger")
    conn.close()
    return redirect(url_for("matches"))


@app.route("/matches/add", methods=["POST"])
def add_match():
    """CREATE — add a new match record."""
    d = request.form
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO matches(tournament_id, venue_id, home_team_id, away_team_id,
                                home_score, away_score, stage, round_num, match_date, attendance)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (d["tournament_id"], d.get("venue_id") or None,
              d["home_team_id"], d["away_team_id"],
              d["home_score"], d["away_score"],
              d["stage"], d.get("round_num") or None,
              d.get("match_date") or None, d.get("attendance") or None))
        # Audit
        conn.execute("INSERT INTO audit_log(table_name,record_id,action,details) VALUES ('matches',last_insert_rowid(),'INSERT',?)",
                     (json.dumps(dict(d)),))
        conn.commit()
        flash("✅ Match added successfully!", "success")
    except Exception as e:
        flash(f"❌ Error: {e}", "danger")
    conn.close()
    return redirect(url_for("matches"))


@app.route("/matches/edit/<int:match_id>", methods=["GET", "POST"])
def edit_match(match_id):
    """UPDATE — edit an existing match."""
    conn = get_connection()
    if request.method == "POST":
        d = request.form
        try:
            conn.execute("""
                UPDATE matches SET home_score=?, away_score=?, stage=?,
                                   attendance=?, match_date=?
                WHERE match_id=?
            """, (d["home_score"], d["away_score"], d["stage"],
                  d.get("attendance") or None, d.get("match_date") or None, match_id))
            conn.execute("INSERT INTO audit_log(table_name,record_id,action,details) VALUES('matches',?,'UPDATE',?)",
                         (match_id, json.dumps(dict(d))))
            conn.commit()
            flash("✅ Match updated!", "success")
        except Exception as e:
            flash(f"❌ Error: {e}", "danger")
        conn.close()
        return redirect(url_for("matches"))

    match = conn.execute("SELECT * FROM vw_matches WHERE match_id=?", (match_id,)).fetchone()
    conn.close()
    return render_template("edit_match.html", match=match)


@app.route("/matches/delete/<int:match_id>", methods=["POST"])
def delete_match(match_id):
    """DELETE (soft) — mark match as deleted and log it."""
    conn = get_connection()
    try:
        conn.execute("UPDATE matches SET is_deleted=1 WHERE match_id=?", (match_id,))
        conn.execute("INSERT INTO audit_log(table_name,record_id,action,details) VALUES('matches',?,'DELETE','soft delete')",
                     (match_id,))
        conn.commit()
        flash("🗑️ Match removed (soft delete logged).", "warning")
    except Exception as e:
        flash(f"❌ {e}", "danger")
    conn.close()
    return redirect(url_for("matches"))


# ─────────────────────────────────────────────
# PLAYERS — READ / CREATE / UPDATE / DELETE
# Author - Jyothi Swaroop Malladi 
# ─────────────────────────────────────────────
@app.route("/players")
def players():
    search    = request.args.get("search", "")
    country   = request.args.get("country", "")
    conn      = get_connection()
    query = """
        SELECT p.player_id, p.name, c.name AS country,
               COALESCE(SUM(ps.goals),0) AS total_goals,
               COALESCE(SUM(ps.matches_played),0) AS total_matches
        FROM players p
        JOIN countries c ON c.country_id = p.country_id
        LEFT JOIN player_stats ps ON ps.player_id = p.player_id
        WHERE p.is_deleted=0
    """
    params = []
    if search:
        query += " AND p.name LIKE ?"; params.append(f"%{search}%")
    if country:
        query += " AND c.name=?"; params.append(country)
    query += " GROUP BY p.player_id ORDER BY total_goals DESC"
    # If no filters applied, only show top 15 players
    if not search and not country:
        query += " LIMIT 15"
    rows      = conn.execute(query, params).fetchall()
    countries = conn.execute("SELECT country_id, name FROM countries ORDER BY name").fetchall()
    conn.close()
    return render_template("players.html", players=rows, countries=countries,
                           filters={"search": search, "country": country},
                           is_filtered=bool(search or country))


@app.route("/players/add", methods=["POST"])
def add_player():
    """CREATE — add player with optional WC goals/matches stored in player_stats."""
    d = request.form
    conn = get_connection()
    try:
        name = d.get("name", "").strip()
        if not name:
            flash("❌ Player name is required.", "danger")
            conn.close()
            return redirect(url_for("players"))

        country_id_raw = d.get("country_id", "")
        # Only reject if literally empty — any numeric string (including "0") is valid
        if country_id_raw == "":
            flash("❌ Please select a country.", "danger")
            conn.close()
            return redirect(url_for("players"))

        try:
            country_id = int(country_id_raw)
        except ValueError:
            flash(f"❌ Invalid country selected (got: '{country_id_raw}').", "danger")
            conn.close()
            return redirect(url_for("players"))

        try:
            wc_goals = int(d.get("wc_goals") or 0)
        except ValueError:
            wc_goals = 0
        try:
            wc_matches = int(d.get("wc_matches") or 0)
        except ValueError:
            wc_matches = 0

        cur = conn.execute(
            "INSERT INTO players(name, country_id, position, birth_year) VALUES (?,?,NULL,NULL)",
            (name, country_id)
        )
        new_id = cur.lastrowid

        if wc_goals > 0 or wc_matches > 0:
            conn.execute(
                """INSERT OR REPLACE INTO player_stats(player_id, tournament_id, goals, assists, matches_played)
                   VALUES (?,0,?,0,?)""",
                (new_id, wc_goals, wc_matches)
            )

        conn.execute(
            "INSERT INTO audit_log(table_name,record_id,action,details) VALUES('players',?,'INSERT',?)",
            (new_id, json.dumps({"name": name, "country_id": country_id,
                                  "wc_goals": wc_goals, "wc_matches": wc_matches}))
        )
        conn.commit()
        flash("✅ Player added!", "success")
    except Exception as e:
        flash(f"❌ {e}", "danger")
    conn.close()
    return redirect(url_for("players", search=d.get("name", "").strip()))


@app.route("/players/edit/<int:player_id>", methods=["GET","POST"])
def edit_player(player_id):
    conn = get_connection()
    if request.method == "POST":
        d = request.form
        try:
            conn.execute(
                "UPDATE players SET name=?, country_id=? WHERE player_id=?",
                (d["name"].strip(), int(d["country_id"]), player_id))
            conn.execute("INSERT INTO audit_log(table_name,record_id,action,details) VALUES('players',?,'UPDATE',?)",
                         (player_id, json.dumps(dict(d))))
            conn.commit()
            flash("✅ Player updated!", "success")
        except Exception as e:
            flash(f"❌ {e}", "danger")
        conn.close()
        return redirect(url_for("players"))
    player = conn.execute("""
        SELECT p.*, c.name as country_name FROM players p
        JOIN countries c ON c.country_id=p.country_id WHERE p.player_id=?
    """, (player_id,)).fetchone()
    countries = conn.execute("SELECT country_id, name FROM countries ORDER BY name").fetchall()
    conn.close()
    return render_template("edit_player.html", player=player, countries=countries)


@app.route("/players/delete/<int:player_id>", methods=["POST"])
def delete_player(player_id):
    conn = get_connection()
    try:
        conn.execute("UPDATE players SET is_deleted=1 WHERE player_id=?", (player_id,))
        conn.execute("INSERT INTO audit_log(table_name,record_id,action,details) VALUES('players',?,'DELETE','soft delete')",
                     (player_id,))
        conn.commit()
        flash("🗑️ Player removed.", "warning")
    except Exception as e:
        flash(f"❌ {e}", "danger")
    conn.close()
    return redirect(url_for("players"))


# ─────────────────────────────────────────────
# COUNTRIES
# ─────────────────────────────────────────────
@app.route("/countries")
def countries():
    conn  = get_connection()
    rows  = conn.execute("""
        SELECT c.name, c.confederation,
               COUNT(DISTINCT m.match_id) AS total_matches,
               COUNT(DISTINCT t.tournament_id) AS tournaments_won
        FROM countries c
        LEFT JOIN matches m ON (m.home_team_id=c.country_id OR m.away_team_id=c.country_id) AND m.is_deleted=0
        LEFT JOIN tournaments t ON LOWER(t.winner)=LOWER(c.name)
        GROUP BY c.country_id ORDER BY tournaments_won DESC, total_matches DESC
    """).fetchall()
    conn.close()
    return render_template("countries.html", countries=rows)


# ─────────────────────────────────────────────
# ANALYTICS / VISUALIZATIONS
# Author - Mohammed Aazam Tadipatri
# ─────────────────────────────────────────────
@app.route("/analytics")
def analytics():
    conn = get_connection()
    # Goals per tournament — only avg_goals_per_match for a clean single line
    # Contributor: Veda Abhishek Kovvireddy
    gpt  = conn.execute("SELECT year, total_goals, avg_goals_per_match FROM vw_goals_per_tournament").fetchall()
    # Top 15 scorers for display
    top  = conn.execute("SELECT player, country, total_goals, matches FROM vw_top_scorers LIMIT 15").fetchall()
    wins = conn.execute("SELECT * FROM vw_country_wins LIMIT 12").fetchall()
    stages = conn.execute("""
        SELECT stage, COUNT(*) as cnt FROM matches WHERE is_deleted=0
        GROUP BY stage ORDER BY cnt DESC
    """).fetchall()
    att = conn.execute("""
        SELECT t.year, COALESCE(SUM(m.attendance), 0) AS total_attendance
        FROM tournaments t
        LEFT JOIN matches m ON m.tournament_id = t.tournament_id
                            AND m.is_deleted = 0
                            AND m.attendance IS NOT NULL
        WHERE t.year > 0
        GROUP BY t.tournament_id ORDER BY t.year
    """).fetchall()
    conn.close()
    return render_template("analytics.html",
                           goals_per_tournament=gpt,
                           top_scorers=top,
                           winners=wins,
                           stages=stages,
                           attendance=att)


# ─────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────
@app.route("/audit")
def audit():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM audit_log ORDER BY changed_at DESC LIMIT 100").fetchall()
    conn.close()
    return render_template("audit.html", logs=rows)


# ─────────────────────────────────────────────
# API ENDPOINTS (JSON) — for JS charts
# ─────────────────────────────────────────────
@app.route("/api/goals_trend")
def api_goals_trend():
    """Single-metric avg goals/match trend — no dual axis. Contributor: Veda Abhishek Kovvireddy"""
    conn = get_connection()
    rows = conn.execute("SELECT year, avg_goals_per_match FROM vw_goals_per_tournament").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/top_scorers")
def api_top_scorers():
    """Top 15 scorers for chart display. Contributor: Mohammed Aazam Tadipatri"""
    conn = get_connection()
    rows = conn.execute("SELECT player, country, total_goals FROM vw_top_scorers LIMIT 15").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/winners")
def api_winners():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM vw_country_wins LIMIT 12").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/attendance")
def api_attendance():
    """Sum attendance from individual match records for accuracy."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.year, COALESCE(SUM(m.attendance), 0) AS total_attendance
        FROM tournaments t
        LEFT JOIN matches m ON m.tournament_id = t.tournament_id
                            AND m.is_deleted = 0
                            AND m.attendance IS NOT NULL
        WHERE t.year > 0
        GROUP BY t.tournament_id
        ORDER BY t.year
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/head2head")
def api_head2head():
    """
    Head-to-head match lookup between two nations.
    Uses exact match first, then falls back to LIKE for flexibility.
    Contributor: Mohammed Aazam Tadipatri
    """
    t1 = request.args.get("team1", "").strip()
    t2 = request.args.get("team2", "").strip()
    conn = get_connection()
    # Exact name match — works whether data is from schema.sql seed or Kaggle ETL
    rows = conn.execute("""
        SELECT DISTINCT vm.year, vm.stage, vm.home_team, vm.away_team,
               vm.home_score, vm.away_score, vm.match_date
        FROM vw_matches vm
        WHERE ((vm.home_team = ? AND vm.away_team = ?)
            OR (vm.home_team = ? AND vm.away_team = ?))
        ORDER BY vm.year
    """, (t1, t2, t2, t1)).fetchall()

    # If no exact results, try LIKE (handles minor name variations)
    if not rows:
        rows = conn.execute("""
            SELECT DISTINCT vm.year, vm.stage, vm.home_team, vm.away_team,
                   vm.home_score, vm.away_score, vm.match_date
            FROM vw_matches vm
            WHERE ((vm.home_team LIKE ? AND vm.away_team LIKE ?)
                OR (vm.home_team LIKE ? AND vm.away_team LIKE ?))
            ORDER BY vm.year
        """, (f"%{t1}%", f"%{t2}%", f"%{t2}%", f"%{t1}%")).fetchall()

    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/countries")
def api_countries():
    conn = get_connection()
    rows = conn.execute("SELECT name FROM countries ORDER BY name").fetchall()
    conn.close()
    return jsonify([r["name"] for r in rows])


# ─────────────────────────────────────────────
# HEAD-TO-HEAD PAGE
# ─────────────────────────────────────────────
@app.route("/head2head")
def head2head():
    conn = get_connection()
    countries = conn.execute("SELECT name FROM countries ORDER BY name").fetchall()
    conn.close()
    return render_template("head2head.html", countries=countries)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if not os.path.exists("fifa.db"):
        init_db()
#   app.run(debug=True, port=5000)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))