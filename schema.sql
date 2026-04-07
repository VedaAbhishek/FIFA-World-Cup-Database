-- ============================================================
-- FIFA World Cup Historical Performance Database
-- schema.sql — DDL + DML
-- Authors: Veda Abhishek Kovvireddy, Jyothi Swaroop Malladi,
--          Mohammed Aazam Tadipatri
-- ============================================================

-- -------------------------------------------------------
-- TABLE: countries
-- Stores each national football team (unique entity).
-- Contributor: Veda Abhishek Kovvireddy
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS countries (
    country_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,   
    confederation TEXT,                     
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -------------------------------------------------------
-- TABLE: tournaments
-- One row per World Cup edition.
-- Contributor: Jyothi Swaroop Malladi
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS tournaments (
    tournament_id INTEGER PRIMARY KEY AUTOINCREMENT,
    year          INTEGER NOT NULL UNIQUE,  
    host_country  TEXT    NOT NULL,
    winner        TEXT,                    
    runner_up     TEXT,
    third_place   TEXT,
    total_goals   INTEGER DEFAULT 0,
    total_matches INTEGER DEFAULT 0,
    total_attendance INTEGER DEFAULT 0
);

-- -------------------------------------------------------
-- TABLE: venues
-- Stadiums where matches were played.
-- Contributor: Mohammed Aazam Tadipatri
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS venues (
    venue_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL,
    country     TEXT NOT NULL,
    capacity    INTEGER,
    UNIQUE(name, city)   
);

-- -------------------------------------------------------
-- TABLE: matches
-- Core fact table; each row = one match.
-- Contributor: Veda Abhishek Kovvireddy
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS matches (
    match_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id   INTEGER NOT NULL REFERENCES tournaments(tournament_id) ON DELETE CASCADE,
    venue_id        INTEGER REFERENCES venues(venue_id),
    home_team_id    INTEGER NOT NULL REFERENCES countries(country_id),
    away_team_id    INTEGER NOT NULL REFERENCES countries(country_id),
    home_score      INTEGER NOT NULL DEFAULT 0 CHECK(home_score >= 0),
    away_score      INTEGER NOT NULL DEFAULT 0 CHECK(away_score >= 0),
    stage           TEXT NOT NULL,         
    round_num       INTEGER,               
    match_date      DATE,
    attendance      INTEGER CHECK(attendance >= 0),
    is_deleted      INTEGER NOT NULL DEFAULT 0 CHECK(is_deleted IN (0,1)), 
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -------------------------------------------------------
-- TABLE: players
-- Deduplicated player registry.
-- Contributor: Jyothi Swaroop Malladi
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS players (
    player_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    country_id  INTEGER NOT NULL REFERENCES countries(country_id),
    position    TEXT,                  -- GK, DF, MF, FW
    birth_year  INTEGER,
    is_deleted  INTEGER NOT NULL DEFAULT 0 CHECK(is_deleted IN (0,1)),
    UNIQUE(name, country_id)           -- same player can only appear once per country
);

-- -------------------------------------------------------
-- TABLE: events
-- Goals, cards, own-goals, penalties per match.
-- Contributor: Mohammed Aazam Tadipatri
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id    INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    player_id   INTEGER REFERENCES players(player_id),
    event_type  TEXT NOT NULL CHECK(event_type IN ('goal','own_goal','yellow_card','red_card','penalty_goal')),
    minute      INTEGER CHECK(minute BETWEEN 1 AND 120),
    team_id     INTEGER REFERENCES countries(country_id)
);

-- -------------------------------------------------------
-- TABLE: player_stats  (derived / aggregated per tournament)
-- Contributor: Veda Abhishek Kovvireddy
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_stats (
    stat_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id     INTEGER NOT NULL REFERENCES players(player_id),
    tournament_id INTEGER NOT NULL REFERENCES tournaments(tournament_id),
    goals         INTEGER DEFAULT 0 CHECK(goals >= 0),
    assists       INTEGER DEFAULT 0 CHECK(assists >= 0),
    matches_played INTEGER DEFAULT 0 CHECK(matches_played >= 0),
    UNIQUE(player_id, tournament_id)
);

-- -------------------------------------------------------
-- TABLE: audit_log  (tracks all deletes / updates for accountability)
-- Contributor: Jyothi Swaroop Malladi
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name  TEXT NOT NULL,
    record_id   INTEGER NOT NULL,
    action      TEXT NOT NULL CHECK(action IN ('INSERT','UPDATE','DELETE')),
    changed_by  TEXT DEFAULT 'app_user',
    changed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details     TEXT       
);

-- ============================================================
-- DML — Seed Data
-- ============================================================

-- --- Countries (Contributor: Mohammed Aazam Tadipatri) ---
-- Note: 'United States' is the single canonical name used across all tables.
-- Duplicates for Iran, Saudi Arabia removed; USA merged into United States.
INSERT OR IGNORE INTO countries(name, confederation) VALUES
('Brazil','CONMEBOL'),('Germany','UEFA'),('Italy','UEFA'),
('Argentina','CONMEBOL'),('France','UEFA'),('England','UEFA'),
('Spain','UEFA'),('Uruguay','CONMEBOL'),('Netherlands','UEFA'),
('Czechoslovakia','UEFA'),('Hungary','UEFA'),('Sweden','UEFA'),
('Poland','UEFA'),('Croatia','UEFA'),('Belgium','UEFA'),
('Portugal','UEFA'),('Mexico','CONCACAF'),('United States','CONCACAF'),
('South Korea','AFC'),('Japan','AFC'),('Senegal','CAF'),
('Morocco','CAF'),('Cameroon','CAF'),('Nigeria','CAF'),
('Australia','AFC'),('Iran','AFC'),('Saudi Arabia','AFC'),
('Ecuador','CONMEBOL'),('Colombia','CONMEBOL'),('Chile','CONMEBOL'),
('Peru','CONMEBOL'),('Paraguay','CONMEBOL'),('Bolivia','CONMEBOL'),
('Austria','UEFA'),('Switzerland','UEFA'),('Denmark','UEFA'),
('Russia','UEFA'),('Romania','UEFA'),('Bulgaria','UEFA'),
('Yugoslavia','UEFA'),('West Germany','UEFA'),('Soviet Union','UEFA'),
('Zaire','CAF'),('North Korea','AFC'),('Haiti','CONCACAF'),
('Cuba','CONCACAF'),('Dutch East Indies','AFC'),
('Turkey','UEFA'),('East Germany','UEFA'),('Ghana','CAF'),
('Serbia','UEFA'),('Canada','CONCACAF'),('Albania','UEFA'),
('Wales','UEFA'),('Tunisia','CAF'),('Costa Rica','CONCACAF'),
('Honduras','CONCACAF'),('Slovenia','UEFA'),('Slovakia','UEFA'),
('El Salvador','CONCACAF'),('Iraq','AFC'),('Kuwait','AFC'),
('Qatar','AFC');

-- --- Tournaments (Contributor: Veda Abhishek Kovvireddy) ---
-- Contributor: Veda Abhishek Kovvireddy
-- All 22 World Cup editions with complete podium data and final attendance figures
INSERT OR IGNORE INTO tournaments(year,host_country,winner,runner_up,third_place,total_goals,total_matches,total_attendance) VALUES
(1930,'Uruguay',    'Uruguay',      'Argentina',     'United States', 70, 18,   434500),
(1934,'Italy',      'Italy',        'Czechoslovakia', 'Germany',        70, 17,   395000),
(1938,'France',     'Italy',        'Hungary',        'Brazil',         84, 18,   483000),
(1950,'Brazil',     'Uruguay',      'Brazil',         'Sweden',         88, 22,  1337000),
(1954,'Switzerland','West Germany', 'Hungary',        'Austria',       140, 26,   943000),
(1958,'Sweden',     'Brazil',       'Sweden',         'France',        126, 35,   868000),
(1962,'Chile',      'Brazil',       'Czechoslovakia', 'Chile',          89, 32,   776000),
(1966,'England',    'England',      'West Germany',   'Portugal',       89, 32,  1614677),
(1970,'Mexico',     'Brazil',       'Italy',          'West Germany',   95, 32,  1673975),
(1974,'West Germany','West Germany','Netherlands',    'Poland',         97, 38,  1774022),
(1978,'Argentina',  'Argentina',    'Netherlands',    'Brazil',        102, 38,  1610215),
(1982,'Spain',      'Italy',        'West Germany',   'Poland',        146, 52,  2109723),
(1986,'Mexico',     'Argentina',    'West Germany',   'France',        132, 52,  2394031),
(1990,'Italy',      'West Germany', 'Argentina',      'Italy',         115, 52,  2516215),
(1994,'United States','Brazil',     'Italy',          'Sweden',        141, 52,  3587538),
(1998,'France',     'France',       'Brazil',         'Croatia',       171, 64,  2785100),
(2002,'South Korea/Japan','Brazil', 'Germany',        'Turkey',        161, 64,  2705197),
(2006,'Germany',    'Italy',        'France',         'Germany',       147, 64,  3359439),
(2010,'South Africa','Spain',       'Netherlands',    'Germany',       145, 64,  3178856),
(2014,'Brazil',     'Germany',      'Argentina',      'Netherlands',   171, 64,  3429873),
(2018,'Russia',     'France',       'Croatia',        'Belgium',       169, 64,  3031768),
(2022,'Qatar',      'Argentina',    'France',         'Croatia',       172, 64,  3404252);

-- --- Venues (Contributor: Jyothi Swaroop Malladi) ---
INSERT OR IGNORE INTO venues(name,city,country,capacity) VALUES
('Maracanã','Rio de Janeiro','Brazil',78838),
('Allianz Arena','Munich','Germany',75000),
('Camp Nou','Barcelona','Spain',99354),
('Wembley Stadium','London','England',90000),
('Azteca Stadium','Mexico City','Mexico',87523),
('Lusail Stadium','Lusail','Qatar',88966),
('San Siro','Milan','Italy',80018),
('Stade de France','Paris','France',81338),
('Soccer City','Johannesburg','South Africa',94700),
('Centenario','Montevideo','Uruguay',65000);

-- --- Matches  (Contributor: Veda Abhishek Kovvireddy) ---
-- Comprehensive historical matches covering all eras and key head-to-head fixtures
-- Ensures head-to-head tool works for major matchups (Brazil vs Argentina, etc.)
INSERT OR IGNORE INTO matches(tournament_id,venue_id,home_team_id,away_team_id,home_score,away_score,stage,round_num,match_date,attendance) VALUES

-- ══ 1930 Uruguay ══
(1,10,(SELECT country_id FROM countries WHERE name='Uruguay'),(SELECT country_id FROM countries WHERE name='Argentina'),4,2,'Final',7,'1930-07-30',68346),
(1,10,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='France'),1,0,'Group Stage',1,'1930-07-15',23000),
(1,10,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Yugoslavia'),1,2,'Group Stage',1,'1930-07-14',24059),
(1,10,(SELECT country_id FROM countries WHERE name='United States'),(SELECT country_id FROM countries WHERE name='Argentina'),1,6,'Semi-finals',6,'1930-07-26',72886),
(1,10,(SELECT country_id FROM countries WHERE name='Uruguay'),(SELECT country_id FROM countries WHERE name='Yugoslavia'),6,1,'Semi-finals',6,'1930-07-27',79867),

-- ══ 1934 Italy ══
(2,NULL,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='Czechoslovakia'),2,1,'Final',7,'1934-06-10',55000),
(2,NULL,(SELECT country_id FROM countries WHERE name='Germany'),(SELECT country_id FROM countries WHERE name='Austria'),3,2,'Semi-finals',6,'1934-06-03',45000),
(2,NULL,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='Austria'),1,0,'Semi-finals',6,'1934-06-03',55000),
(2,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Spain'),1,3,'Round of 16',2,'1934-05-27',7000),

-- ══ 1938 France ══
(3,NULL,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='Hungary'),4,2,'Final',7,'1938-06-19',45000),
(3,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Sweden'),4,2,'Semi-finals',6,'1938-06-16',23500),
(3,NULL,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='Brazil'),2,1,'Semi-finals',6,'1938-06-16',58000),
(3,NULL,(SELECT country_id FROM countries WHERE name='Cuba'),(SELECT country_id FROM countries WHERE name='Romania'),2,1,'Round of 16',2,'1938-06-05',6000),

-- ══ 1950 Brazil ══
(4,1,(SELECT country_id FROM countries WHERE name='Uruguay'),(SELECT country_id FROM countries WHERE name='Brazil'),2,1,'Final',7,'1950-07-16',199854),
(4,1,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Sweden'),7,1,'Group Stage',1,'1950-07-09',138886),
(4,1,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Spain'),6,1,'Group Stage',1,'1950-07-13',152772),
(4,1,(SELECT country_id FROM countries WHERE name='Uruguay'),(SELECT country_id FROM countries WHERE name='Spain'),3,2,'Group Stage',1,'1950-07-14',79867),
(4,1,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Yugoslavia'),2,0,'Group Stage',1,'1950-07-01',142429),

-- ══ 1954 Switzerland ══
(5,NULL,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='Hungary'),3,2,'Final',7,'1954-07-04',62500),
(5,NULL,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='Austria'),6,1,'Semi-finals',6,'1954-06-30',58000),
(5,NULL,(SELECT country_id FROM countries WHERE name='Hungary'),(SELECT country_id FROM countries WHERE name='Uruguay'),4,2,'Semi-finals',6,'1954-06-30',57000),
(5,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Hungary'),2,4,'Quarter-finals',3,'1954-06-27',40000),

-- ══ 1958 Sweden ══
(6,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Sweden'),5,2,'Final',7,'1958-06-29',51800),
(6,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='France'),5,2,'Semi-finals',6,'1958-06-24',27000),
(6,NULL,(SELECT country_id FROM countries WHERE name='Sweden'),(SELECT country_id FROM countries WHERE name='West Germany'),3,1,'Semi-finals',6,'1958-06-24',49471),
(6,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Argentina'),0,0,'Group Stage',1,'1958-06-08',22000),

-- ══ 1962 Chile ══
(7,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Czechoslovakia'),3,1,'Final',7,'1962-06-17',68679),
(7,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Chile'),4,2,'Semi-finals',6,'1962-06-13',76594),
(7,NULL,(SELECT country_id FROM countries WHERE name='Czechoslovakia'),(SELECT country_id FROM countries WHERE name='Yugoslavia'),3,1,'Semi-finals',6,'1962-06-13',5890),
(7,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='England'),3,1,'Quarter-finals',3,'1962-06-10',17736),
(7,NULL,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Hungary'),0,0,'Group Stage',1,'1962-06-03',7945),

-- ══ 1966 England ══
(8,4,(SELECT country_id FROM countries WHERE name='England'),(SELECT country_id FROM countries WHERE name='West Germany'),4,2,'Final',7,'1966-07-30',96924),
(8,4,(SELECT country_id FROM countries WHERE name='England'),(SELECT country_id FROM countries WHERE name='Portugal'),2,1,'Semi-finals',6,'1966-07-26',94493),
(8,4,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='Soviet Union'),2,1,'Semi-finals',6,'1966-07-25',88000),
(8,4,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='England'),0,1,'Quarter-finals',3,'1966-07-23',90584),
(8,4,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Portugal'),1,3,'Group Stage',1,'1966-07-19',58479),
(8,4,(SELECT country_id FROM countries WHERE name='Portugal'),(SELECT country_id FROM countries WHERE name='North Korea'),5,3,'Quarter-finals',3,'1966-07-23',40248),

-- ══ 1970 Mexico ══
(9,5,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Italy'),4,1,'Final',7,'1970-06-21',107412),
(9,5,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Uruguay'),3,1,'Semi-finals',6,'1970-06-17',51261),
(9,5,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='West Germany'),4,3,'Semi-finals',6,'1970-06-17',102444),
(9,5,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='England'),1,0,'Group Stage',1,'1970-06-07',70950),
(9,5,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Argentina'),0,0,'Quarter-finals',3,'1970-06-10',52897),
(9,5,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Czechoslovakia'),4,1,'Group Stage',1,'1970-06-03',49557),
(9,5,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='England'),3,2,'Quarter-finals',3,'1970-06-14',23357),
(9,5,(SELECT country_id FROM countries WHERE name='Peru'),(SELECT country_id FROM countries WHERE name='Bulgaria'),3,2,'Group Stage',1,'1970-06-02',13537),

-- ══ 1974 West Germany ══
(10,NULL,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='Netherlands'),2,1,'Final',7,'1974-07-07',75200),
(10,NULL,(SELECT country_id FROM countries WHERE name='Poland'),(SELECT country_id FROM countries WHERE name='Brazil'),1,0,'Semi-finals',6,'1974-07-03',38100),
(10,NULL,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='Poland'),1,0,'Semi-finals',6,'1974-07-03',62000),
(10,NULL,(SELECT country_id FROM countries WHERE name='Netherlands'),(SELECT country_id FROM countries WHERE name='Brazil'),2,0,'Semi-finals',6,'1974-07-03',61000),
(10,NULL,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='East Germany'),0,1,'Group Stage',1,'1974-06-22',60200),
(10,NULL,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Brazil'),1,2,'Group Stage',1,'1974-06-26',54000),

-- ══ 1978 Argentina ══
(11,NULL,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Netherlands'),3,1,'Final',7,'1978-06-25',71483),
(11,NULL,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Brazil'),0,0,'Group Stage',1,'1978-06-18',67547),
(11,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Poland'),3,1,'Group Stage',1,'1978-06-21',40735),
(11,NULL,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='Argentina'),1,0,'Group Stage',1,'1978-06-10',77260),
(11,NULL,(SELECT country_id FROM countries WHERE name='Netherlands'),(SELECT country_id FROM countries WHERE name='Italy'),2,1,'Semi-finals',6,'1978-06-21',65000),

-- ══ 1982 Spain ══
(12,3,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='West Germany'),3,1,'Final',7,'1982-07-11',90000),
(12,3,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='Brazil'),3,2,'Group Stage',1,'1982-07-05',44000),
(12,NULL,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='France'),3,3,'Semi-finals',6,'1982-07-08',71000),
(12,3,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Brazil'),1,3,'Group Stage',1,'1982-07-02',44000),
(12,3,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Argentina'),3,1,'Group Stage',1,'1982-06-02',44000),
(12,3,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Argentina'),1,0,'Group Stage',1,'1982-06-13',37000),
(12,3,(SELECT country_id FROM countries WHERE name='England'),(SELECT country_id FROM countries WHERE name='France'),3,1,'Group Stage',1,'1982-06-16',44172),

-- ══ 1986 Mexico ══
(13,5,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='West Germany'),3,2,'Final',7,'1986-06-29',114600),
(13,5,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Belgium'),2,0,'Semi-finals',6,'1986-06-25',110420),
(13,5,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='France'),2,0,'Semi-finals',6,'1986-06-25',114580),
(13,5,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='England'),2,1,'Quarter-finals',3,'1986-06-22',114580),
(13,5,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='France'),4,4,'Quarter-finals',3,'1986-06-21',65000),
(13,5,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Brazil'),1,0,'Quarter-finals',3,'1986-06-21',114580),
(13,5,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Argentina'),0,1,'Quarter-finals',3,'1986-06-21',65000),

-- ══ 1990 Italy ══
(14,7,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='Argentina'),1,0,'Final',7,'1990-07-08',73603),
(14,7,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Italy'),1,1,'Semi-finals',6,'1990-07-03',59978),
(14,7,(SELECT country_id FROM countries WHERE name='West Germany'),(SELECT country_id FROM countries WHERE name='England'),1,1,'Semi-finals',6,'1990-07-04',62628),
(14,7,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Brazil'),1,0,'Round of 16',2,'1990-06-24',61381),
(14,7,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Argentina'),0,1,'Round of 16',2,'1990-06-24',61381),
(14,7,(SELECT country_id FROM countries WHERE name='England'),(SELECT country_id FROM countries WHERE name='Belgium'),1,0,'Round of 16',2,'1990-06-26',34520),
(14,7,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='Argentina'),2,0,'Group Stage',1,'1990-06-30',59978),

-- ══ 1994 USA ══
(15,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Italy'),0,0,'Final',7,'1994-07-17',94194),
(15,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Sweden'),1,0,'Semi-finals',6,'1994-07-13',84569),
(15,NULL,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='Bulgaria'),2,1,'Semi-finals',6,'1994-07-13',74110),
(15,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Netherlands'),3,2,'Quarter-finals',3,'1994-07-09',94194),
(15,NULL,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Romania'),3,2,'Round of 16',2,'1994-07-03',60246),
(15,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Argentina'),1,0,'Round of 16',2,'1994-07-04',94194),

-- ══ 1998 France ══
(16,8,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Brazil'),3,0,'Final',7,'1998-07-12',80000),
(16,8,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Netherlands'),1,1,'Semi-finals',6,'1998-07-07',76000),
(16,8,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Croatia'),2,1,'Semi-finals',6,'1998-07-08',76000),
(16,8,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Netherlands'),1,2,'Quarter-finals',3,'1998-07-04',80000),
(16,8,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Italy'),0,0,'Quarter-finals',3,'1998-07-03',77000),
(16,8,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Argentina'),0,0,'Group Stage',1,'1998-07-04',76000),

-- ══ 2002 South Korea/Japan ══
(17,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Germany'),2,0,'Final',7,'2002-06-30',69029),
(17,NULL,(SELECT country_id FROM countries WHERE name='Germany'),(SELECT country_id FROM countries WHERE name='South Korea'),1,0,'Semi-finals',6,'2002-06-25',65256),
(17,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Turkey'),1,0,'Semi-finals',6,'2002-06-26',61058),
(17,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='England'),2,1,'Quarter-finals',3,'2002-06-21',52061),
(17,NULL,(SELECT country_id FROM countries WHERE name='South Korea'),(SELECT country_id FROM countries WHERE name='Germany'),0,1,'Semi-finals',6,'2002-06-25',65256),
(17,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Argentina'),1,0,'Round of 16',2,'2002-06-24',66000),

-- ══ 2006 Germany ══
(18,2,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='France'),1,1,'Final',7,'2006-07-09',69000),
(18,2,(SELECT country_id FROM countries WHERE name='Italy'),(SELECT country_id FROM countries WHERE name='Germany'),2,0,'Semi-finals',6,'2006-07-04',65000),
(18,2,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Portugal'),1,0,'Semi-finals',6,'2006-07-05',66000),
(18,2,(SELECT country_id FROM countries WHERE name='Germany'),(SELECT country_id FROM countries WHERE name='Argentina'),1,1,'Quarter-finals',3,'2006-06-30',72000),
(18,2,(SELECT country_id FROM countries WHERE name='England'),(SELECT country_id FROM countries WHERE name='Portugal'),0,0,'Quarter-finals',3,'2006-07-01',66000),
(18,2,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Brazil'),NULL,NULL,'Group Stage',1,'2006-06-10',66000),
(18,2,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='France'),1,0,'Quarter-finals',3,'2006-06-21',60000),

-- ══ 2010 South Africa ══
(19,9,(SELECT country_id FROM countries WHERE name='Spain'),(SELECT country_id FROM countries WHERE name='Netherlands'),1,0,'Final',7,'2010-07-11',84490),
(19,9,(SELECT country_id FROM countries WHERE name='Spain'),(SELECT country_id FROM countries WHERE name='Germany'),1,0,'Semi-finals',6,'2010-07-07',84490),
(19,9,(SELECT country_id FROM countries WHERE name='Netherlands'),(SELECT country_id FROM countries WHERE name='Uruguay'),3,2,'Semi-finals',6,'2010-07-06',62479),
(19,9,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Germany'),0,4,'Quarter-finals',3,'2010-07-03',83359),
(19,9,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Netherlands'),1,2,'Quarter-finals',3,'2010-07-02',82294),
(19,9,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Brazil'),NULL,NULL,'Group Stage',1,'2010-06-20',80000),
(19,9,(SELECT country_id FROM countries WHERE name='England'),(SELECT country_id FROM countries WHERE name='Germany'),1,4,'Round of 16',2,'2010-06-27',46570),

-- ══ 2014 Brazil ══
(20,1,(SELECT country_id FROM countries WHERE name='Germany'),(SELECT country_id FROM countries WHERE name='Argentina'),1,0,'Final',7,'2014-07-13',74738),
(20,1,(SELECT country_id FROM countries WHERE name='Germany'),(SELECT country_id FROM countries WHERE name='Brazil'),7,1,'Semi-finals',6,'2014-07-08',58141),
(20,1,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Netherlands'),0,0,'Semi-finals',6,'2014-07-09',64511),
(20,1,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Colombia'),2,1,'Quarter-finals',3,'2014-07-04',68551),
(20,1,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Germany'),0,1,'Quarter-finals',3,'2014-07-04',74240),
(20,1,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Belgium'),1,0,'Quarter-finals',3,'2014-07-05',73819),
(20,1,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Brazil'),NULL,NULL,'Group Stage',1,'2014-06-15',64000),
(20,1,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Croatia'),3,1,'Group Stage',1,'2014-06-12',62103),

-- ══ 2018 Russia ══
(21,NULL,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Croatia'),4,2,'Final',7,'2018-07-15',78011),
(21,NULL,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Belgium'),1,0,'Semi-finals',6,'2018-07-10',74894),
(21,NULL,(SELECT country_id FROM countries WHERE name='Croatia'),(SELECT country_id FROM countries WHERE name='England'),2,1,'Semi-finals',6,'2018-07-11',78011),
(21,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Belgium'),1,2,'Quarter-finals',3,'2018-07-06',78011),
(21,NULL,(SELECT country_id FROM countries WHERE name='England'),(SELECT country_id FROM countries WHERE name='Sweden'),2,0,'Quarter-finals',3,'2018-07-07',44190),
(21,NULL,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Argentina'),4,3,'Round of 16',2,'2018-06-30',40714),
(21,NULL,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='France'),3,4,'Round of 16',2,'2018-06-30',40714),
(21,NULL,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Argentina'),NULL,NULL,'Group Stage',1,'2018-06-20',58000),
(21,NULL,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Croatia'),0,3,'Group Stage',1,'2018-06-21',42612),
(21,NULL,(SELECT country_id FROM countries WHERE name='England'),(SELECT country_id FROM countries WHERE name='Belgium'),0,1,'Group Stage',1,'2018-06-28',35489),

-- ══ 2022 Qatar ══
(22,6,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='France'),3,3,'Final',7,'2022-12-18',88966),
(22,6,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Croatia'),3,0,'Semi-finals',6,'2022-12-13',88966),
(22,6,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Morocco'),2,0,'Semi-finals',6,'2022-12-14',88966),
(22,6,(SELECT country_id FROM countries WHERE name='Netherlands'),(SELECT country_id FROM countries WHERE name='Argentina'),2,2,'Quarter-finals',5,'2022-12-09',88235),
(22,6,(SELECT country_id FROM countries WHERE name='Morocco'),(SELECT country_id FROM countries WHERE name='Portugal'),1,0,'Quarter-finals',5,'2022-12-10',88020),
(22,6,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='England'),2,1,'Quarter-finals',5,'2022-12-10',88235),
(22,6,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Croatia'),1,1,'Quarter-finals',5,'2022-12-09',88196),
(22,6,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Australia'),2,1,'Round of 16',2,'2022-12-03',88012),
(22,6,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Poland'),3,1,'Round of 16',2,'2022-12-04',88235),
(22,6,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='South Korea'),4,1,'Round of 16',2,'2022-12-05',88966),
(22,6,(SELECT country_id FROM countries WHERE name='England'),(SELECT country_id FROM countries WHERE name='Senegal'),3,0,'Round of 16',2,'2022-12-04',65547),
(22,6,(SELECT country_id FROM countries WHERE name='Portugal'),(SELECT country_id FROM countries WHERE name='Switzerland'),6,1,'Round of 16',2,'2022-12-06',88966),
(22,6,(SELECT country_id FROM countries WHERE name='Germany'),(SELECT country_id FROM countries WHERE name='Japan'),1,2,'Group Stage',1,'2022-11-23',47513),
(22,6,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Serbia'),2,0,'Group Stage',1,'2022-11-24',88103),
(22,6,(SELECT country_id FROM countries WHERE name='England'),(SELECT country_id FROM countries WHERE name='Iran'),6,2,'Group Stage',1,'2022-11-21',45334),
(22,6,(SELECT country_id FROM countries WHERE name='Spain'),(SELECT country_id FROM countries WHERE name='Germany'),1,1,'Group Stage',1,'2022-11-27',68015),
(22,6,(SELECT country_id FROM countries WHERE name='Argentina'),(SELECT country_id FROM countries WHERE name='Saudi Arabia'),1,2,'Group Stage',1,'2022-11-22',88012),
(22,6,(SELECT country_id FROM countries WHERE name='France'),(SELECT country_id FROM countries WHERE name='Denmark'),2,1,'Group Stage',1,'2022-11-26',89012),
(22,6,(SELECT country_id FROM countries WHERE name='Brazil'),(SELECT country_id FROM countries WHERE name='Switzerland'),1,0,'Group Stage',1,'2022-11-28',88020),
(22,6,(SELECT country_id FROM countries WHERE name='Portugal'),(SELECT country_id FROM countries WHERE name='Ghana'),3,2,'Group Stage',1,'2022-11-24',89012),
(22,6,(SELECT country_id FROM countries WHERE name='Morocco'),(SELECT country_id FROM countries WHERE name='Belgium'),2,0,'Group Stage',1,'2022-11-27',44137),
(22,6,(SELECT country_id FROM countries WHERE name='Croatia'),(SELECT country_id FROM countries WHERE name='Canada'),4,1,'Group Stage',1,'2022-11-27',44137);

-- --- Players (Contributor: Mohammed Aazam Tadipatri) ---
INSERT OR IGNORE INTO players(name,country_id,position,birth_year) VALUES
('Pelé',(SELECT country_id FROM countries WHERE name='Brazil'),'FW',1940),
('Diego Maradona',(SELECT country_id FROM countries WHERE name='Argentina'),'FW',1960),
('Ronaldo Nazário',(SELECT country_id FROM countries WHERE name='Brazil'),'FW',1976),
('Zinedine Zidane',(SELECT country_id FROM countries WHERE name='France'),'MF',1972),
('Miroslav Klose',(SELECT country_id FROM countries WHERE name='Germany'),'FW',1978),
('Gerd Müller',(SELECT country_id FROM countries WHERE name='West Germany'),'FW',1945),
('Just Fontaine',(SELECT country_id FROM countries WHERE name='France'),'FW',1933),
('Ronaldo',(SELECT country_id FROM countries WHERE name='Portugal'),'FW',1985),
('Lionel Messi',(SELECT country_id FROM countries WHERE name='Argentina'),'FW',1987),
('Kylian Mbappé',(SELECT country_id FROM countries WHERE name='France'),'FW',1998),
('Luka Modrić',(SELECT country_id FROM countries WHERE name='Croatia'),'MF',1985),
('Oliver Kahn',(SELECT country_id FROM countries WHERE name='Germany'),'GK',1969),
('Paolo Maldini',(SELECT country_id FROM countries WHERE name='Italy'),'DF',1968),
('Eusébio',(SELECT country_id FROM countries WHERE name='Portugal'),'FW',1942),
('Gareth Bale',(SELECT country_id FROM countries WHERE name='England'),'FW',1989),
('Harry Kane',(SELECT country_id FROM countries WHERE name='England'),'FW',1993),
('Lothar Matthäus',(SELECT country_id FROM countries WHERE name='Germany'),'MF',1961),
('Johan Cruyff',(SELECT country_id FROM countries WHERE name='Netherlands'),'FW',1947),
('Rivaldo',(SELECT country_id FROM countries WHERE name='Brazil'),'FW',1972),
('Thierry Henry',(SELECT country_id FROM countries WHERE name='France'),'FW',1977);

-- --- Player Stats (Contributor: Veda Abhishek Kovvireddy) ---
INSERT OR IGNORE INTO player_stats(player_id,tournament_id,goals,assists,matches_played) VALUES
-- Miroslav Klose — all-time top scorer (16 goals across 4 WCs)
((SELECT player_id FROM players WHERE name='Miroslav Klose'),(SELECT tournament_id FROM tournaments WHERE year=2002),5,0,7),
((SELECT player_id FROM players WHERE name='Miroslav Klose'),(SELECT tournament_id FROM tournaments WHERE year=2006),5,1,7),
((SELECT player_id FROM players WHERE name='Miroslav Klose'),(SELECT tournament_id FROM tournaments WHERE year=2010),4,0,6),
((SELECT player_id FROM players WHERE name='Miroslav Klose'),(SELECT tournament_id FROM tournaments WHERE year=2014),2,1,6),
-- Ronaldo Nazário
((SELECT player_id FROM players WHERE name='Ronaldo Nazário'),(SELECT tournament_id FROM tournaments WHERE year=1994),0,0,2),
((SELECT player_id FROM players WHERE name='Ronaldo Nazário'),(SELECT tournament_id FROM tournaments WHERE year=1998),4,2,7),
((SELECT player_id FROM players WHERE name='Ronaldo Nazário'),(SELECT tournament_id FROM tournaments WHERE year=2002),8,1,7),
((SELECT player_id FROM players WHERE name='Ronaldo Nazário'),(SELECT tournament_id FROM tournaments WHERE year=2006),3,0,5),
-- Just Fontaine 1958 (13 goals — single tournament record)
((SELECT player_id FROM players WHERE name='Just Fontaine'),(SELECT tournament_id FROM tournaments WHERE year=1958),13,0,6),
-- Pelé
((SELECT player_id FROM players WHERE name='Pelé'),(SELECT tournament_id FROM tournaments WHERE year=1958),6,0,6),
((SELECT player_id FROM players WHERE name='Pelé'),(SELECT tournament_id FROM tournaments WHERE year=1962),1,0,2),
((SELECT player_id FROM players WHERE name='Pelé'),(SELECT tournament_id FROM tournaments WHERE year=1966),1,0,2),
((SELECT player_id FROM players WHERE name='Pelé'),(SELECT tournament_id FROM tournaments WHERE year=1970),4,2,6),
-- Maradona
((SELECT player_id FROM players WHERE name='Diego Maradona'),(SELECT tournament_id FROM tournaments WHERE year=1982),2,0,5),
((SELECT player_id FROM players WHERE name='Diego Maradona'),(SELECT tournament_id FROM tournaments WHERE year=1986),5,5,7),
((SELECT player_id FROM players WHERE name='Diego Maradona'),(SELECT tournament_id FROM tournaments WHERE year=1990),1,3,7),
-- Messi
((SELECT player_id FROM players WHERE name='Lionel Messi'),(SELECT tournament_id FROM tournaments WHERE year=2006),1,0,3),
((SELECT player_id FROM players WHERE name='Lionel Messi'),(SELECT tournament_id FROM tournaments WHERE year=2010),0,1,5),
((SELECT player_id FROM players WHERE name='Lionel Messi'),(SELECT tournament_id FROM tournaments WHERE year=2014),4,1,7),
((SELECT player_id FROM players WHERE name='Lionel Messi'),(SELECT tournament_id FROM tournaments WHERE year=2018),1,0,4),
((SELECT player_id FROM players WHERE name='Lionel Messi'),(SELECT tournament_id FROM tournaments WHERE year=2022),7,3,7),
-- Mbappé
((SELECT player_id FROM players WHERE name='Kylian Mbappé'),(SELECT tournament_id FROM tournaments WHERE year=2018),4,0,7),
((SELECT player_id FROM players WHERE name='Kylian Mbappé'),(SELECT tournament_id FROM tournaments WHERE year=2022),8,2,7),
-- Zidane
((SELECT player_id FROM players WHERE name='Zinedine Zidane'),(SELECT tournament_id FROM tournaments WHERE year=1998),2,2,7),
((SELECT player_id FROM players WHERE name='Zinedine Zidane'),(SELECT tournament_id FROM tournaments WHERE year=2002),0,0,3),
((SELECT player_id FROM players WHERE name='Zinedine Zidane'),(SELECT tournament_id FROM tournaments WHERE year=2006),3,1,7),
-- Gerd Müller
((SELECT player_id FROM players WHERE name='Gerd Müller'),(SELECT tournament_id FROM tournaments WHERE year=1970),10,0,6),
((SELECT player_id FROM players WHERE name='Gerd Müller'),(SELECT tournament_id FROM tournaments WHERE year=1974),4,0,7),
-- Eusébio 1966
((SELECT player_id FROM players WHERE name='Eusébio'),(SELECT tournament_id FROM tournaments WHERE year=1966),9,0,6);

-- --- Events — sample goal events (Contributor: Jyothi Swaroop Malladi) ---
INSERT OR IGNORE INTO events(match_id,player_id,event_type,minute,team_id) VALUES
-- 2022 Final: Argentina vs France (match_id=12)
(12,(SELECT player_id FROM players WHERE name='Lionel Messi'),'goal',23,(SELECT country_id FROM countries WHERE name='Argentina')),
(12,NULL,'own_goal',36,(SELECT country_id FROM countries WHERE name='France')),
(12,(SELECT player_id FROM players WHERE name='Kylian Mbappé'),'goal',80,(SELECT country_id FROM countries WHERE name='France')),
(12,(SELECT player_id FROM players WHERE name='Kylian Mbappé'),'penalty_goal',81,(SELECT country_id FROM countries WHERE name='France')),
(12,(SELECT player_id FROM players WHERE name='Lionel Messi'),'goal',108,(SELECT country_id FROM countries WHERE name='Argentina')),
(12,(SELECT player_id FROM players WHERE name='Kylian Mbappé'),'goal',118,(SELECT country_id FROM countries WHERE name='France'));

-- ============================================================
-- VIEWS — useful analytical queries
-- ============================================================

-- Top scorers all-time (Contributor: Mohammed Aazam Tadipatri)
CREATE VIEW IF NOT EXISTS vw_top_scorers AS
SELECT p.name AS player, c.name AS country,
       SUM(ps.goals) AS total_goals,
       SUM(ps.matches_played) AS matches,
       ROUND(CAST(SUM(ps.goals) AS REAL)/NULLIF(SUM(ps.matches_played),0),2) AS goals_per_match
FROM player_stats ps
JOIN players p ON p.player_id = ps.player_id AND p.is_deleted = 0
JOIN countries c ON c.country_id = p.country_id
WHERE ps.tournament_id != 0
GROUP BY p.player_id
ORDER BY total_goals DESC;

-- Goals per tournament trend (Contributor: Veda Abhishek Kovvireddy)
CREATE VIEW IF NOT EXISTS vw_goals_per_tournament AS
SELECT year, host_country, winner, total_goals, total_matches,
       ROUND(CAST(total_goals AS REAL)/NULLIF(total_matches,0),2) AS avg_goals_per_match
FROM tournaments
WHERE year > 0
ORDER BY year;

-- Country win counts (Contributor: Jyothi Swaroop Malladi)
CREATE VIEW IF NOT EXISTS vw_country_wins AS
SELECT winner AS country, COUNT(*) AS titles
FROM tournaments
WHERE winner IS NOT NULL AND year > 0
GROUP BY winner
ORDER BY titles DESC;

-- Match results with team names (Contributor: Mohammed Aazam Tadipatri)
-- DISTINCT prevents duplicate rows when the same match_id appears via multiple joins
CREATE VIEW IF NOT EXISTS vw_matches AS
SELECT DISTINCT
       m.match_id, t.year, m.stage, m.round_num, m.match_date,
       h.name AS home_team, a.name AS away_team,
       m.home_score, m.away_score, m.attendance,
       v.name AS venue, v.city
FROM matches m
JOIN tournaments t ON t.tournament_id = m.tournament_id
JOIN countries h ON h.country_id = m.home_team_id
JOIN countries a ON a.country_id = m.away_team_id
LEFT JOIN venues v ON v.venue_id = m.venue_id
WHERE m.is_deleted = 0
ORDER BY t.year, m.round_num;
