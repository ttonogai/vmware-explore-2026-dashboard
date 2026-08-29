#!/usr/bin/env python3
"""index.html 内のJSを抽出して Node で構文チェック + 集計ロジックを実行検証する。"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path('/home/tono/work/kiro/202608_Explore_LasVegas')
html = (BASE / 'index.html').read_text(encoding='utf-8')

# JSON実データから期待値を算出（HAR更新に追従させるため固定値を使わない）
_S = json.loads((BASE / 'sessions_full.json').read_text(encoding='utf-8'))
_S_cap = sum(s['capacity'] or 0 for s in _S)
_S_rem = sum(s['seats_remaining'] or 0 for s in _S)
_S_wl = sum(1 for s in _S if s['availability_status'] == 'Waitlist')

script = re.search(r'<script>(.*)</script>', html, re.S)
if not script:
    sys.exit('ERROR: scriptタグが見つかりません')
js = script.group(1)

with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
    f.write(js)
    syntax_file = f.name

r = subprocess.run(['node', '--check', syntax_file], capture_output=True, text=True)
print("== JS構文チェック ==")
if r.returncode == 0:
    print("  OK    構文エラーなし")
else:
    print("  FAIL  " + r.stderr.strip()[:800])
    sys.exit(1)

stub = r'''
const __els = {};
function __mk(id){
  return {
    id, innerHTML:'', textContent:'', value:'', className:'', dataset:{},
    style:{}, classList:{toggle(){}, add(){}, remove(){}},
    addEventListener(){}, appendChild(){}, querySelector(){return null;},
    querySelectorAll(){return [];}, remove(){}
  };
}
const __ths = [
  'code','title','track','level','product','additional_products',
  'speakers','day','fill_rate','availability_status'
].map(k => { const e = __mk('th_'+k); e.dataset = {key:k}; return e; });

global.document = {
  getElementById(id){ if(!__els[id]) __els[id] = __mk(id); return __els[id]; },
  querySelectorAll(sel){ return sel.includes('th[data-key]') ? __ths : []; },
  createElement(tag){ return __mk('el_'+tag); }
};
'''

tail = r'''
const out = {
  total, waitlist: waitlist.length, sponsored: sponsored.length,
  peoplesChoice: peoplesChoice.length, productCount,
  totalCap, totalRem, fillPct: +fillPct.toFixed(1),
  trackCounts, levelCounts, productTop,
  kpiCards: (__els['kpi'].innerHTML.match(/class="kpi/g)||[]).length,
  trackChartRendered: __els['c-track'].innerHTML.length > 0,
  levelChartRendered: __els['c-level'].innerHTML.length > 0,
  productChartRendered: __els['c-product'].innerHTML.length > 0,
  crossRendered: __els['c-cross'].innerHTML.length > 0,
  fillRendered: __els['c-fill'].innerHTML.length > 0,
  topRows: (__els['c-top'].innerHTML.match(/class="top-row/g)||[]).length,
  topHtml: __els['c-top'].innerHTML,
  topNote: __els['top-note'].textContent,
  topBooked: topSessions.map(s => (s.capacity||0)-(s.seats_remaining||0)),
  topCodes: topSessions.map(s => s.code),
  waitlistRendered: __els['waitlist-list'].innerHTML.length > 0,
  pcRendered: __els['pc-list'].innerHTML.length > 0,
  tbodyRendered: __els['tbody'].innerHTML.length > 0,
  wlSub: __els['wl-sub'].textContent,
  crossNote: __els['cross-note'].textContent,
  fillNote: __els['fill-note'].textContent,
  metaText: __els['meta'].textContent,
  wlHead: __els['wl-head'].textContent,
  pcHead: __els['pc-head'].textContent,
  tblHead: __els['tbl-head'].textContent,
  kpiHtml: __els['kpi'].innerHTML,
  tbodyHtml: __els['tbody'].innerHTML,
  crossTotalsMatch: trackCounts.reduce((a,x)=>a+x[1],0) === total,
  levelTotalsMatch: levelCounts.reduce((a,x)=>a+x[1],0) === total
};
console.log(JSON.stringify(out, null, 1));
'''

with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
    f.write(stub + js + tail)
    run_file = f.name

r2 = subprocess.run(['node', run_file], capture_output=True, text=True)
print("\n== JS実行検証（DOMスタブ） ==")
if r2.returncode != 0:
    print("  FAIL  実行時エラー:")
    print('  ' + r2.stderr.strip()[:1500].replace('\n', '\n  '))
    sys.exit(1)

res = json.loads(r2.stdout)
ok = True


def check(label, cond, extra=''):
    global ok
    print(f"  {'OK  ' if cond else 'FAIL'}  {label}" + (f"  {extra}" if extra else ''))
    if not cond:
        ok = False


_exp_sp = sum(1 for s in _S if s['is_sponsored'])
_exp_pc = sum(1 for s in _S if s['is_peoples_choice'])
check(f'全セッション数 = JSONと一致 ({len(_S)})', res['total'] == len(_S), f"→ {res['total']}")
check(f'満席 = JSONと一致 ({_S_wl})', res['waitlist'] == _S_wl, f"→ {res['waitlist']}")
check(f'スポンサー = JSONと一致 ({_exp_sp})', res['sponsored'] == _exp_sp, f"→ {res['sponsored']}")
check(f"People's Choice = JSONと一致 ({_exp_pc})", res['peoplesChoice'] == _exp_pc, f"→ {res['peoplesChoice']}")
check('製品数 > 0', res['productCount'] > 0, f"→ {res['productCount']}")
check(f'総座席 = JSONと一致 ({_S_cap:,})', res['totalCap'] == _S_cap, f"→ {res['totalCap']:,}")
_exp_fill = round((_S_cap - _S_rem) / _S_cap * 100, 1)
check(f'充填率 = JSONと一致 ({_exp_fill}%)', abs(res['fillPct'] - _exp_fill) < 0.1, f"→ {res['fillPct']}%")
check('Track合計 = 総数', res['crossTotalsMatch'])
check('Level合計 = 総数', res['levelTotalsMatch'])
check('KPIカードが5枚', res['kpiCards'] == 5, f"→ {res['kpiCards']}枚")

print("\n  -- 人気セッション Top10 --")
check('10行描画されている', res['topRows'] == 10, f"→ {res['topRows']}行")
check('申込数が降順に並んでいる',
      all(res['topBooked'][i] >= res['topBooked'][i + 1] for i in range(len(res['topBooked']) - 1)),
      f"→ {res['topBooked']}")
check('上位3件に top3 クラスが付く', res['topHtml'].count('top-row top3') == 3,
      f"→ {res['topHtml'].count('top-row top3')}件")
check('1位が最大申込数', res['topBooked'][0] == max(res['topBooked']), f"→ {res['topBooked'][0]}名")
check('注記が生成されている', len(res['topNote']) > 10)
print(f"    Top10コード: {', '.join(res['topCodes'])}")
print(f"    申込数     : {res['topBooked']}")
print(f"    注記       : {res['topNote']}")

print("\n  -- 削除した要素が残っていないか --")
check('KPIに「直近追加」がない', '直近追加' not in res['kpiHtml'])
check('KPIに「製品数」がある', '製品数' in res['kpiHtml'])
check('テーブルに New バッジがない', 'badge-new' not in res['tbodyHtml'])

print("\n  -- 描画されたブロック --")
for label, key in [
    ('Track別', 'trackChartRendered'), ('Level別', 'levelChartRendered'),
    ('Product別', 'productChartRendered'), ('クロス集計', 'crossRendered'),
    ('Track別充填率', 'fillRendered'), ('満席リスト', 'waitlistRendered'),
    ("People's Choice", 'pcRendered'), ('一覧テーブル', 'tbodyRendered'),
]:
    check(label, res[key])

print("\n  -- 生成テキスト --")
print(f"    meta       : {res['metaText']}")
print(f"    満席見出し  : {res['wlHead']}")
print(f"    満席内訳    : {res['wlSub']}")
print(f"    PC見出し    : {res['pcHead']}")
print(f"    表見出し    : {res['tblHead']}")
print(f"    クロス注記  : {res['crossNote']}")
print(f"    充填注記    : {res['fillNote']}")

Path(syntax_file).unlink(missing_ok=True)
Path(run_file).unlink(missing_ok=True)

print("\n" + ('=== ALL CHECKS PASSED ===' if ok else '=== FAILURES DETECTED ==='))
sys.exit(0 if ok else 1)
