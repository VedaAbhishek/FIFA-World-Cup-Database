# ⚽ FIFA World Cup Performance Database

**Course:** Applied Database Design — IU Bloomington  
**Team:** Veda Abhishek Kovvireddy · Jyothi Swaroop Malladi · Mohammed Aazam Tadipatri  
**Dataset:** [Kaggle — FIFA World Cup (abecklas)](https://www.kaggle.com/datasets/abecklas/fifa-world-cup)

---

## Quick Start

### 1. Install Python dependencies

```bash
pip install flask pandas
```

### 2. Download the Kaggle dataset

Go to: https://www.kaggle.com/datasets/abecklas/fifa-world-cup  
Download and **unzip**. Place the 3 CSV files into the `data/` folder:

```
fifa_worldcup/
└── data/
    ├── WorldCups.csv
    ├── WorldCupMatches.csv
    └── WorldCupPlayers.csv
```

### 3. Build the database from the real Kaggle data

```bash
python load_kaggle_data.py
```

This reads all 3 CSVs, normalizes country names, and populates `fifa.db` with real historical data (~850 matches, ~37,000 player rows, goals/cards events).

### 4. Run the app

```bash
python app.py
```

Open: http://127.0.0.1:5000

---

## Project Structure

```
fifa_worldcup/
├── app.py                  # Flask routes — full CRUD + analytics
├── db.py                   # DB connection helper
├── schema.sql              # DDL: tables, constraints, indexes, views
├── load_kaggle_data.py     # ETL: reads Kaggle CSVs → fifa.db  ← NEW
├── requirements.txt
├── data/                   # Place Kaggle CSVs here (not committed to git)
│   ├── WorldCups.csv
│   ├── WorldCupMatches.csv
│   └── WorldCupPlayers.csv
└── templates/
    ├── base.html
    ├── index.html
    ├── tournaments.html
    ├── matches.html
    ├── players.html
    ├── countries.html
    ├── analytics.html
    ├── head2head.html
    ├── audit.html
    ├── edit_match.html
    └── edit_player.html
```

---

## What load_kaggle_data.py does

| Step | Source                | Tables populated                    |
| ---- | --------------------- | ----------------------------------- |
| 1    | `schema.sql` DDL only | All tables + views created          |
| 2    | `WorldCups.csv`       | `countries`, `tournaments`          |
| 3    | `WorldCupMatches.csv` | `venues`, `matches`                 |
| 4    | `WorldCupPlayers.csv` | `players`, `player_stats`, `events` |

**Normalization handled automatically:**

- `"Germany FR"` → `"West Germany"`
- `"Korea Republic"` → `"South Korea"`
- `"C?te d'Ivoire"` / `"Côte d'Ivoire"` → `"Ivory Coast"`
- `"USA"` → `"United States"`
- Attendance strings with commas (`"3,587,538"`) parsed correctly
- Dates like `"13 Jul 1930 - 15:00"` converted to `1930-07-13`
- Player event strings like `"G23' G67' Y88'"` parsed into structured events

---

## Acknowledgements

- **Data:** Kaggle FIFA World Cup dataset by abecklas  
  https://www.kaggle.com/datasets/abecklas/fifa-world-cup
- **AI Assistance:** ETL and route logic reviewed using Claude (Anthropic, claude-sonnet-4-20250514), accessed April 2026, for normalization patterns and SQL consistency checks.
- **AI Assistance:** ChatGPT - SQL syntax review, regex edge case checking, column name mismatch resolution.
- **Flask docs:** https://flask.palletsprojects.com/en/3.0.x/
