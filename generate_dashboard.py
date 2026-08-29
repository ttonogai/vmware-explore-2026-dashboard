#!/usr/bin/env python3
"""テンプレートに sessions_full.json を埋め込んで dashboard.html を生成する。

集計はすべてブラウザ側のJSで行うため、HARを差し替えて
  python3 extract_from_har.py && python3 generate_dashboard.py
を実行すれば数値・グラフ・表がまとめて更新される。
"""
import json
import re
from pathlib import Path

BASE = Path('/home/tono/work/kiro/202608_Explore_LasVegas')
TEMPLATE_PATH = BASE / 'dashboard_template.html'
OUTPUT_PATH = BASE / 'index.html'
DATA_PATH = BASE / 'sessions_full.json'
HAR_PATH = BASE / 'event.vmware.com_20260830.har'

sessions = json.loads(DATA_PATH.read_text(encoding='utf-8'))
html = TEMPLATE_PATH.read_text(encoding='utf-8')

# HARファイル名から取得日を推定（なければ更新日時）
m = re.search(r'(\d{4})(\d{2})(\d{2})', HAR_PATH.name)
capture_date = f"{m.group(1)}/{int(m.group(2))}/{int(m.group(3))}" if m else '不明'

if 'SESSIONS_DATA_PLACEHOLDER' not in html:
    raise SystemExit('ERROR: テンプレートに SESSIONS_DATA_PLACEHOLDER がありません')

html = html.replace('SESSIONS_DATA_PLACEHOLDER', json.dumps(sessions, ensure_ascii=False))
html = html.replace('CAPTURE_DATE_PLACEHOLDER', capture_date)
OUTPUT_PATH.write_text(html, encoding='utf-8')

waitlist = sum(1 for s in sessions if s['availability_status'] == 'Waitlist')
cap = sum(s['capacity'] or 0 for s in sessions)
rem = sum(s['seats_remaining'] or 0 for s in sessions)

print(f"Dashboard generated: {OUTPUT_PATH}")
print(f"  sessions      : {len(sessions)}")
print(f"  waitlist      : {waitlist}")
print(f"  fill rate     : {(cap - rem) / cap * 100:.1f}%  ({cap - rem:,}/{cap:,})")
print(f"  capture date  : {capture_date}")
print(f"  size          : {OUTPUT_PATH.stat().st_size:,} bytes")
