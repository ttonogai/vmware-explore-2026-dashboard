#!/usr/bin/env python3
"""Import parsed session data into SQLite, outputting INSERT statements."""
import json

with open('/home/tono/work/kiro/202608_Explore_LasVegas/sessions_parsed.json', 'r', encoding='utf-8') as f:
    sessions = json.load(f)

for s in sessions:
    title = s['title'].replace("'", "''")
    desc = s['description'].replace("'", "''").replace('\n', ' ')[:200]
    code = s['code']
    track = s['track']
    day = s['day']
    ts = s['time_start']
    te = s['time_end']
    pc = s['is_peoples_choice']
    sp = s['is_sponsored']
    av = s['availability']
    print(f"INSERT OR IGNORE INTO breakout_sessions (session_code, title, track, day, time_start, time_end, description, is_peoples_choice, is_sponsored, availability_status) VALUES ('{code}', '{title}', '{track}', '{day}', '{ts}', '{te}', '{desc}', {pc}, {sp}, '{av}');")
