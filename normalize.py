import sqlite3

conn = sqlite3.connect("fifa.db")
cur = conn.cursor()

print("Connected to database")


# =========================
# 1NF
# =========================
cur.executescript("""
DROP TABLE IF EXISTS T_1NF;

CREATE TABLE T_1NF (
    MatchID INTEGER,
    Year INTEGER,
    MatchDate TEXT,
    Stage TEXT,
    Stadium TEXT,
    City TEXT,
    HomeTeam TEXT,
    HomeScore INTEGER,
    AwayScore INTEGER,
    AwayTeam TEXT,
    Attendance INTEGER
);

INSERT INTO T_1NF
SELECT
    m.match_id,
    t.year,
    m.match_date,
    m.stage,
    v.name,
    v.city,
    c1.name,
    m.home_score,
    m.away_score,
    c2.name,
    m.attendance
FROM matches m
JOIN tournaments t ON m.tournament_id = t.tournament_id
JOIN countries c1 ON m.home_team_id = c1.country_id
JOIN countries c2 ON m.away_team_id = c2.country_id
LEFT JOIN venues v ON m.venue_id = v.venue_id;

UPDATE T_1NF SET HomeTeam = TRIM(HomeTeam);
UPDATE T_1NF SET AwayTeam = TRIM(AwayTeam);
UPDATE T_1NF SET Stadium = TRIM(Stadium);
UPDATE T_1NF SET City = TRIM(City);
""")

conn.commit()

print("\n--- 1NF OUTPUT ---")
cur.execute("SELECT * FROM T_1NF LIMIT 10;")
print([col[0] for col in cur.description])
for row in cur.fetchall():
    print(row)

# =========================
# 2NF
# =========================
cur.executescript("""
DROP TABLE IF EXISTS Tournaments_2NF;
DROP TABLE IF EXISTS Teams_2NF;
DROP TABLE IF EXISTS Venues_2NF;
DROP TABLE IF EXISTS Matches_2NF;

CREATE TABLE Tournaments_2NF AS
SELECT tournament_id, year, host_country
FROM tournaments;

CREATE TABLE Teams_2NF AS
SELECT country_id, name AS TeamName, confederation
FROM countries;

CREATE TABLE Venues_2NF AS
SELECT venue_id, name AS Stadium, city, country
FROM venues;

CREATE TABLE Matches_2NF AS
SELECT
    match_id,
    tournament_id,
    venue_id,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    stage,
    round_num,
    match_date,
    attendance
FROM matches;
""")

conn.commit()

print("\n--- 2NF OUTPUT ---")
cur.execute("""
SELECT
    m.match_id,
    t.year,
    v.Stadium,
    v.city,
    c1.TeamName AS HomeTeam,
    m.home_score,
    m.away_score,
    c2.TeamName AS AwayTeam,
    m.stage,
    m.match_date
FROM Matches_2NF m
JOIN Tournaments_2NF t ON m.tournament_id = t.tournament_id
JOIN Teams_2NF c1 ON m.home_team_id = c1.country_id
JOIN Teams_2NF c2 ON m.away_team_id = c2.country_id
LEFT JOIN Venues_2NF v ON m.venue_id = v.venue_id
LIMIT 10;
""")

print([col[0] for col in cur.description])
for row in cur.fetchall():
    print(row)

# =========================
# 3NF
# =========================
cur.executescript("""
DROP TABLE IF EXISTS Countries_3NF;
DROP TABLE IF EXISTS Tournaments_3NF;
DROP TABLE IF EXISTS Venues_3NF;
DROP TABLE IF EXISTS Matches_3NF;

CREATE TABLE Countries_3NF AS
SELECT country_id, name, confederation
FROM countries;

CREATE TABLE Tournaments_3NF AS
SELECT tournament_id, year, host_country
FROM tournaments;

CREATE TABLE Venues_3NF AS
SELECT venue_id, name AS Stadium, city, country
FROM venues;

CREATE TABLE Matches_3NF AS
SELECT
    match_id,
    tournament_id,
    venue_id,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    stage,
    round_num,
    match_date,
    attendance
FROM matches;
""")

conn.commit()

print("\n--- 3NF OUTPUT ---")
cur.execute("""
SELECT
    m.match_id,
    t.year,
    v.Stadium,
    v.city,
    c1.name AS HomeTeam,
    m.home_score,
    m.away_score,
    c2.name AS AwayTeam,
    m.stage,
    m.match_date
FROM Matches_3NF m
JOIN Tournaments_3NF t ON m.tournament_id = t.tournament_id
JOIN Countries_3NF c1 ON m.home_team_id = c1.country_id
JOIN Countries_3NF c2 ON m.away_team_id = c2.country_id
LEFT JOIN Venues_3NF v ON m.venue_id = v.venue_id
LIMIT 10;
""")

print([col[0] for col in cur.description])
for row in cur.fetchall():
    print(row)

# =========================
# 4NF
# =========================
cur.executescript("""
DROP TABLE IF EXISTS Players_4NF;
DROP TABLE IF EXISTS PlayerStats_4NF;
DROP TABLE IF EXISTS Events_4NF;

-- Players (independent entity)
CREATE TABLE Players_4NF AS
SELECT
    player_id,
    name,
    country_id,
    position
FROM players;

-- Player stats (player ↔ tournament relationship)
CREATE TABLE PlayerStats_4NF AS
SELECT
    player_id,
    tournament_id,
    goals,
    matches_played
FROM player_stats;

-- Events (match ↔ events multivalued dependency)
CREATE TABLE Events_4NF AS
SELECT
    event_id,
    match_id,
    player_id,
    event_type,
    minute,
    team_id
FROM events;
""")

conn.commit()

# PRINT 4NF OUTPUT
print("\n--- 4NF OUTPUT ---")

cur.execute("""
SELECT
    e.match_id,
    p.name AS Player,
    e.event_type,
    e.minute
FROM Events_4NF e
JOIN Players_4NF p 
    ON e.player_id = p.player_id
LIMIT 10;
""")

# Print column names
print([col[0] for col in cur.description])

# Print rows
for row in cur.fetchall():
    print(row)