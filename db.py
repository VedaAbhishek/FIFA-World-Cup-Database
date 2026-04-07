"""
db.py — SQLite connection helper and initializer
Authors: Veda Abhishek Kovvireddy, Jyothi Swaroop Malladi, Mohammed Aazam Tadipatri
AI Assistance: Code structure scaffolded with Claude (Anthropic), accessed April 2026.
"""
import sqlite3
import os

DB_PATH     = os.path.join(os.path.dirname(__file__), "fifa.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

def get_connection():
    """Return a SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # Ensure the career-aggregate tournament (id=0) always exists so manually
    # added player stats never hit a FK violation.
    conn.execute("""
        INSERT OR IGNORE INTO tournaments(tournament_id, year, host_country,
            winner, total_goals, total_matches, total_attendance)
        VALUES (0, 0, 'Career Entry', NULL, 0, 0, 0)
    """)
    conn.commit()
    return conn

def init_db():
    """Apply DDL-only (no seed data) — real data comes from load_kaggle_data.py."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        raw = f.read()
    ddl_only = raw.split("-- DML — Seed Data")[0]
    conn = get_connection()
    conn.executescript(ddl_only)
    conn.commit()
    conn.close()
    print(f"[DB] Initialized → {DB_PATH}")