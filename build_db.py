#!/usr/bin/env python3
"""Build SQLite DB from parsed session JSON."""
import json
import sqlite3

DB_PATH = '/home/tono/work/kiro/202608_Explore_LasVegas/explore2026.db'

with open('/home/tono/work/kiro/202608_Explore_LasVegas/sessions_parsed.json', 'r', encoding='utf-8') as f:
    sessions = json.load(f)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute('DROP TABLE IF EXISTS breakout_sessions')
cur.execute('''CREATE TABLE breakout_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_code TEXT UNIQUE,
    title TEXT,
    track TEXT,
    day TEXT,
    time_start TEXT,
    time_end TEXT,
    description TEXT,
    is_peoples_choice INTEGER DEFAULT 0,
    is_sponsored INTEGER DEFAULT 0,
    availability_status TEXT DEFAULT 'Available'
)''')

for s in sessions:
    cur.execute('''INSERT OR IGNORE INTO breakout_sessions 
        (session_code, title, track, day, time_start, time_end, description, is_peoples_choice, is_sponsored, availability_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (s['code'], s['title'], s['track'], s['day'], s['time_start'], s['time_end'],
         s['description'][:300], s['is_peoples_choice'], s['is_sponsored'], s['availability']))

conn.commit()
print(f"Inserted {cur.execute('SELECT COUNT(*) FROM breakout_sessions').fetchone()[0]} sessions")

# Print summary
print("\n=== Track Summary ===")
for row in cur.execute('SELECT track, COUNT(*) as cnt FROM breakout_sessions GROUP BY track ORDER BY cnt DESC'):
    print(f"  {row[0]}: {row[1]}")

print("\n=== Availability ===")
for row in cur.execute('SELECT availability_status, COUNT(*) FROM breakout_sessions GROUP BY availability_status'):
    print(f"  {row[0]}: {row[1]}")

print("\n=== Waitlist Sessions ===")
for row in cur.execute('SELECT session_code, title, track, day, time_start FROM breakout_sessions WHERE availability_status = "Waitlist"'):
    print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} {row[4]}")

print("\n=== Day Distribution ===")
for row in cur.execute("""SELECT 
    CASE 
        WHEN day LIKE '%Mon%' AND day NOT LIKE '%;%' THEN 'Mon Only'
        WHEN day LIKE '%Tue%' AND day NOT LIKE '%;%' THEN 'Tue Only'  
        WHEN day LIKE '%Wed%' AND day NOT LIKE '%;%' THEN 'Wed Only'
        WHEN day LIKE '%;%' THEN 'Multiple Days'
        ELSE 'Unknown'
    END as day_group, COUNT(*) 
    FROM breakout_sessions GROUP BY day_group ORDER BY COUNT(*) DESC"""):
    print(f"  {row[0]}: {row[1]}")

print("\n=== Sponsored Sessions ===")
print(f"  Sponsored: {cur.execute('SELECT COUNT(*) FROM breakout_sessions WHERE is_sponsored=1').fetchone()[0]}")
print(f"  Non-sponsored: {cur.execute('SELECT COUNT(*) FROM breakout_sessions WHERE is_sponsored=0').fetchone()[0]}")

conn.close()
