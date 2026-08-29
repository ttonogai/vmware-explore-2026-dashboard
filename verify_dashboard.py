#!/usr/bin/env python3
"""生成された index.html の健全性を検証する。"""
import json
import re
import sys
from pathlib import Path

BASE = Path('/home/tono/work/kiro/202608_Explore_LasVegas')
html = (BASE / 'index.html').read_text(encoding='utf-8')
sessions = json.loads((BASE / 'sessions_full.json').read_text(encoding='utf-8'))

ok = True


def check(label, cond, detail=''):
    global ok
    print(f"  {'OK  ' if cond else 'FAIL'}  {label}" + (f"  -- {detail}" if detail and not cond else ''))
    if not cond:
        ok = False


print("== プレースホルダ ==")
check('SESSIONS_DATA_PLACEHOLDER が置換済み', 'SESSIONS_DATA_PLACEHOLDER' not in html)
check('CAPTURE_DATE_PLACEHOLDER が置換済み', 'CAPTURE_DATE_PLACEHOLDER' not in html)

print("\n== 埋め込みJSONの整合性 ==")
m = re.search(r'^const S = (\[.*\]);$', html, re.M)
check('const S = [...] が抽出できる', m is not None)
if m:
    try:
        embedded = json.loads(m.group(1))
        check('埋め込みJSONがパース可能', True)
        check(f'件数一致 ({len(embedded)} == {len(sessions)})', len(embedded) == len(sessions))
        keys_needed = ['code', 'title', 'track', 'level', 'product', 'additional_products',
                       'day', 'time_start', 'capacity', 'seats_remaining', 'fill_rate',
                       'speakers_detail', 'is_sponsored', 'is_peoples_choice',
                       'recently_added', 'availability_status']
        missing = [k for k in keys_needed if k not in embedded[0]]
        check('必須キーが揃っている', not missing, f'missing={missing}')
        check('speakers_detail が全件入っている',
              all(e.get('speakers_detail') for e in embedded))
        wl = sum(1 for e in embedded if e['availability_status'] == 'Waitlist')
        check(f'満席件数 = 28 (実測 {wl})', wl == 28)
        srz = sum(1 for e in embedded if e['seats_remaining'] == 0)
        check(f'seats_remaining==0 と満席が一致 ({srz})', srz == wl)
    except json.JSONDecodeError as ex:
        check('埋め込みJSONがパース可能', False, str(ex))

print("\n== DOM要素とJSの対応 ==")
ids_in_js = set(re.findall(r"getElementById\('([^']+)'\)", html))
ids_in_html = set(re.findall(r'id="([^"]+)"', html))
missing_ids = sorted(ids_in_js - ids_in_html)
check('JSが参照する全idがHTMLに存在', not missing_ids, f'missing={missing_ids}')

print("\n== 削除済み要素が残っていないか ==")
check('ツリーマップ(tm-cell)が残っていない', 'tm-cell' not in html)
check('treemap要素が残っていない', 'id="treemap"' not in html)

print("\n== 期待コンテンツ ==")
for label, needle in [
    ('Track別カード', 'id="c-track"'),
    ('Level別カード', 'id="c-level"'),
    ('Product別カード', 'id="c-product"'),
    ('クロス集計カード', 'id="c-cross"'),
    ('Track別充填率カード', 'id="c-fill"'),
    ('人気Top10カード', 'id="c-top"'),
    ('満席リスト', 'id="waitlist-list"'),
    ("People's Choiceリスト", 'id="pc-list"'),
    ('一覧テーブル', 'id="tbody"'),
    ('充填率列ヘッダ', 'data-key="fill_rate"'),
]:
    check(label, needle in html)

print("\n== 削除済み要素が残っていないか ==")
check('Day別カードが削除済み', 'id="c-day"' not in html)
check('新規追加フィルタが削除済み', 'id="f-new"' not in html)
check('フッター注記が削除済み', 'データソース' not in html)

print("\n== 取得日 ==")
m2 = re.search(r"const CAPTURED = '([^']*)'", html)
check('CAPTURED が設定されている', bool(m2 and m2.group(1)), '')
if m2:
    print(f"        capture date = {m2.group(1)}")

print("\n" + ('=== ALL CHECKS PASSED ===' if ok else '=== FAILURES DETECTED ==='))
sys.exit(0 if ok else 1)
