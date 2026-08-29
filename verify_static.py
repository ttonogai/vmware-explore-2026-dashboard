#!/usr/bin/env python3
"""index.html が GitHub Pages 等の静的ホスティングで自己完結して動くか検証する。"""
import re
import sys
from pathlib import Path

BASE = Path('/home/tono/work/kiro/202608_Explore_LasVegas')
path = BASE / 'index.html'
html = path.read_text(encoding='utf-8')

ok = True


def check(label, cond, detail=''):
    global ok
    print(f"  {'OK  ' if cond else 'NG  '}  {label}" + (f"  -- {detail}" if detail else ''))
    if not cond:
        ok = False


print("== 外部リソース参照（あると外部通信が発生する） ==")
patterns = {
    '<script src=...>': r'<script[^>]+src=',
    '<link rel=stylesheet>': r'<link[^>]+stylesheet',
    '<img src=...>': r'<img[^>]+src=',
    '<iframe>': r'<iframe',
    '@import': r'@import',
    'url(http...) in CSS': r'url\(\s*[\'"]?https?:',
    'fetch(': r'\bfetch\s*\(',
    'XMLHttpRequest': r'XMLHttpRequest',
    'axios': r'\baxios\b',
    'import from': r'^\s*import\s.+from\s',
    'require(': r'\brequire\s*\(',
    'WebSocket': r'\bWebSocket\b',
    'document.write': r'document\.write',
}
for label, pat in patterns.items():
    found = re.findall(pat, html, re.M | re.I)
    check(f'{label} なし', not found, f'{len(found)}件検出' if found else '')

print("\n== 自己完結性 ==")
check('<style> にCSSが内包されている', '<style>' in html and 'body{' in html.replace(' ', ''))
check('<script> にJSが内包されている', '<script>' in html)
check('データがインライン埋め込み (const S = [)', bool(re.search(r'const S = \[\{', html)))
check('外部データファイル読み込みなし',
      not re.search(r"(fetch|XMLHttpRequest)[^\n]*\.json", html))

print("\n== HTTPで壊れやすい要素 ==")
check('絶対ローカルパス(file:///)なし', 'file:///' not in html)
check('WSLパス(/home/)がHTML内に埋め込まれていない', '/home/tono' not in html)
check('mixed content (http://) なし', not re.findall(r'src=["\']http://|href=["\']http://', html))
check('DOCTYPE宣言あり', html.lstrip().lower().startswith('<!doctype html'))
check('charset=UTF-8 宣言あり', re.search(r'charset=["\']?utf-8', html, re.I) is not None)
check('viewport メタタグあり（モバイル対応）', 'name="viewport"' in html)
check('lang属性あり', re.search(r'<html[^>]+lang=', html) is not None)

print("\n== フォント ==")
ff = re.findall(r"font-family:([^;}]+)", html)
uses_webfont = any('link' in html and 'fonts.googleapis' in html for _ in [0])
check('Webフォントの外部読み込みなし（システムフォントにフォールバック）', not uses_webfont)
if ff:
    print(f"        font-family: {ff[0].strip()[:90]}")

print("\n== ファイルサイズ ==")
size = path.stat().st_size
check(f'GitHub Pages の推奨上限内 (実測 {size/1024/1024:.2f} MB < 100 MB)', size < 100 * 1024 * 1024)
check(f'初回表示が重すぎない (実測 {size/1024:.0f} KB)', size < 5 * 1024 * 1024,
      '5MB超は表示が重くなる可能性')

print("\n== GitHub Pages 固有 ==")
check('Jekyll処理で問題になる {{ }} 構文なし', '{{' not in html and '{%' not in html)
check('ファイル名が index.html である', path.name == 'index.html',
      f'現在 "{path.name}" → 公開時は index.html にリネームか .nojekyll+パス指定が必要')

print("\n" + ('=== 静的ホスティング適合 ===' if ok else '=== 要対応あり（上記NG参照）==='))
sys.exit(0)
