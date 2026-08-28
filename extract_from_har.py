#!/usr/bin/env python3
"""HARからBreakout Session情報を抽出し、SQLite/JSONへ保存する。

前回版との差分:
  - HARパスを 20260828 版に更新
  - Waitlist判定をハードコードから seatsRemaining ベースの実データに変更
  - capacity / seats_remaining / fill_rate を保持
  - recently_added フラグを追加
"""
import json
import sqlite3
from collections import Counter

HAR_PATH = '/home/tono/work/kiro/202608_Explore_LasVegas/event.vmware.com_20260828.har'
DB_PATH = '/home/tono/work/kiro/202608_Explore_LasVegas/explore2026.db'
JSON_PATH = '/home/tono/work/kiro/202608_Explore_LasVegas/sessions_full.json'

print("Loading HAR file...")
with open(HAR_PATH, 'r', encoding='utf-8') as f:
    har = json.load(f)

# /api/sessions のレスポンスから全セッションを集約
all_items = []
seen_codes = set()

for e in har['log']['entries']:
    if '/api/sessions' not in e['request']['url']:
        continue
    text = (e.get('response', {}).get('content', {}) or {}).get('text', '') or ''
    if not text:
        continue
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        continue
    if not isinstance(data, dict):
        continue

    items_list = []
    for section in data.get('sectionList', []) or []:
        items_list.extend(section.get('items', []) or [])
    if isinstance(data.get('items'), list):
        items_list.extend(data['items'])

    for item in items_list:
        code = item.get('code', '')
        if code and code not in seen_codes:
            seen_codes.add(code)
            all_items.append(item)

print(f"Total unique sessions from HAR: {len(all_items)}")

# Breakout Session のみに絞る
breakout_items = []
for item in all_items:
    for av in item.get('attributevalues', []) or []:
        if av.get('attribute_id') == 'SessionType' and av.get('value') == 'Breakout Session':
            breakout_items.append(item)
            break

print(f"Breakout Sessions: {len(breakout_items)}")

sessions = []
for item in breakout_items:
    code = item.get('code', '')
    title = item.get('title', '')

    track = ''
    level = ''
    product = ''
    additional_products = []
    is_sponsored = 0
    is_peoples_choice = 0
    recently_added = 0
    sponsor_company = ''

    for av in item.get('attributevalues', []) or []:
        attr_id = av.get('attribute_id', '')
        value = av.get('value', '')
        if attr_id == 'Track':
            track = value
        elif attr_id == 'Level':
            level = value
        elif attr_id == 'Product':
            product = value
        elif attr_id == 'AdditionalProducts':
            additional_products.append(value)
        elif attr_id == 'SponsorSession':
            is_sponsored = 1
        elif attr_id == 'SponsorCompanyName':
            sponsor_company = value
        elif attr_id == 'PeoplesChoiceSession':
            is_peoples_choice = 1
        elif attr_id == 'RecentlyAdded':
            recently_added = 1

    # 時間・部屋・座席情報
    times = item.get('times') or []
    day = time_start = time_end = room = ''
    capacity = 0
    seats_remaining = None

    if times:
        t = times[0]
        day_name = (t.get('dayDisplayName') or '')[:3]
        month = (t.get('longMonth') or '')[:3]
        day_num = t.get('day', '')
        day = f"{day_name} {month} {day_num}".strip()
        time_start = t.get('startTime', '')
        time_end = t.get('endTimeFormatted', '')
        room = t.get('room', '')
        try:
            capacity = int(t.get('capacity') or 0)
        except (TypeError, ValueError):
            capacity = 0
        sr = t.get('seatsRemaining')
        if isinstance(sr, int):
            seats_remaining = sr

    # 充填率（capacity が取れている場合のみ）
    if capacity > 0 and seats_remaining is not None:
        fill_rate = round((capacity - seats_remaining) / capacity * 100, 1)
    else:
        fill_rate = None

    availability = 'Waitlist' if seats_remaining == 0 else 'Available'

    # スピーカー
    speakers = []
    speakers_detail = []
    for p in item.get('participants', []) or []:
        name = p.get('fullName') or f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
        job = p.get('jobTitle', '')
        company = p.get('companyName', '')
        if not name:
            continue
        speakers.append(name)
        detail = name
        if job:
            detail += f" ({job}, {company})" if company else f" ({job})"
        elif company:
            detail += f" ({company})"
        speakers_detail.append(detail)

    sessions.append({
        'code': code,
        'title': title,
        'track': track,
        'level': level,
        'product': product,
        'additional_products': ', '.join(additional_products),
        'day': day,
        'time_start': time_start,
        'time_end': time_end,
        'room': room,
        'capacity': capacity,
        'seats_remaining': seats_remaining,
        'fill_rate': fill_rate,
        'speakers': ', '.join(speakers),
        'speakers_detail': ' | '.join(speakers_detail),
        'description': (item.get('abstract') or '')[:500],
        'is_peoples_choice': is_peoples_choice,
        'is_sponsored': is_sponsored,
        'sponsor_company': sponsor_company,
        'recently_added': recently_added,
        'availability_status': availability,
    })

print(f"Parsed sessions: {len(sessions)}")

# SQLite へ保存
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute('DROP TABLE IF EXISTS breakout_sessions')
cur.execute('''CREATE TABLE breakout_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_code TEXT UNIQUE,
    title TEXT,
    track TEXT,
    level TEXT,
    product TEXT,
    additional_products TEXT,
    day TEXT,
    time_start TEXT,
    time_end TEXT,
    room TEXT,
    capacity INTEGER,
    seats_remaining INTEGER,
    fill_rate REAL,
    speakers TEXT,
    speakers_detail TEXT,
    description TEXT,
    is_peoples_choice INTEGER DEFAULT 0,
    is_sponsored INTEGER DEFAULT 0,
    sponsor_company TEXT,
    recently_added INTEGER DEFAULT 0,
    availability_status TEXT DEFAULT 'Available'
)''')

cur.executemany('''INSERT OR IGNORE INTO breakout_sessions
    (session_code, title, track, level, product, additional_products, day, time_start, time_end,
     room, capacity, seats_remaining, fill_rate, speakers, speakers_detail, description,
     is_peoples_choice, is_sponsored, sponsor_company, recently_added, availability_status)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
    [(s['code'], s['title'], s['track'], s['level'], s['product'], s['additional_products'],
      s['day'], s['time_start'], s['time_end'], s['room'], s['capacity'], s['seats_remaining'],
      s['fill_rate'], s['speakers'], s['speakers_detail'], s['description'],
      s['is_peoples_choice'], s['is_sponsored'], s['sponsor_company'], s['recently_added'],
      s['availability_status']) for s in sessions])
conn.commit()

# サマリ出力
print(f"\n{'='*64}")
print(f"DB Updated: {cur.execute('SELECT COUNT(*) FROM breakout_sessions').fetchone()[0]} sessions")
print(f"{'='*64}")

print("\n## Availability")
for r in cur.execute('SELECT availability_status, COUNT(*) FROM breakout_sessions GROUP BY availability_status ORDER BY 2 DESC'):
    print(f"  {r[0]:12s} {r[1]:3d}")

print("\n## Track Distribution")
for r in cur.execute('SELECT track, COUNT(*) c FROM breakout_sessions GROUP BY track ORDER BY c DESC'):
    print(f"  {r[0] or '(none)':28s} {r[1]:3d}")

print("\n## Level Distribution")
for r in cur.execute('SELECT level, COUNT(*) c FROM breakout_sessions GROUP BY level ORDER BY c DESC'):
    print(f"  {r[0] or '(none)':28s} {r[1]:3d}")

print("\n## Day Distribution")
for r in cur.execute('SELECT day, COUNT(*) c FROM breakout_sessions GROUP BY day ORDER BY c DESC'):
    print(f"  {r[0] or '(none)':28s} {r[1]:3d}")

print("\n## 充填率トップ15")
for r in cur.execute('''SELECT session_code, capacity, seats_remaining, fill_rate, substr(title,1,46)
                        FROM breakout_sessions WHERE fill_rate IS NOT NULL
                        ORDER BY fill_rate DESC, capacity DESC LIMIT 15'''):
    print(f"  {r[0]:12s} cap={r[1]:>4d} rem={r[2]:>5d} {r[3]:>6.1f}%  {r[4]}")

print("\n## その他")
print(f"  スポンサーセッション: {cur.execute('SELECT COUNT(*) FROM breakout_sessions WHERE is_sponsored=1').fetchone()[0]}")
print(f"  People's Choice     : {cur.execute('SELECT COUNT(*) FROM breakout_sessions WHERE is_peoples_choice=1').fetchone()[0]}")
print(f"  Recently Added      : {cur.execute('SELECT COUNT(*) FROM breakout_sessions WHERE recently_added=1').fetchone()[0]}")
tot_cap, tot_rem = cur.execute('SELECT SUM(capacity), SUM(seats_remaining) FROM breakout_sessions').fetchone()
print(f"  総座席数            : {tot_cap:,} / 残席 {tot_rem:,} (全体充填率 {(tot_cap-tot_rem)/tot_cap*100:.1f}%)")

conn.close()

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(sessions, f, ensure_ascii=False, indent=2)
print(f"\nSaved {JSON_PATH}")
