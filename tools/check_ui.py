"""Check localization/ui/batch_<i>_ko.json against batch_<i>.json.

  python tools/check_ui.py 3
Rules checked: every unit translated; every {RAW:..} control token of the
Japanese kept in order (name tokens RAW 9380... must become {NAME:id:이름});
{PAGE} count equal; no Japanese kana/kanji left.
"""
import sys, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
UI = ROOT/'localization/ui'
JP = re.compile(r'[぀-ヿ一-鿿々]')

def ctrl(s):
    return [t for t in re.findall(r'\{RAW:([0-9a-fA-F]+)\}', s) if not t.lower().startswith('9380')]

def names(s):
    return len(re.findall(r'\{RAW:9380[0-9a-fA-F]*\}', s))

def main(i):
    src = json.loads((UI/f'batch_{i}.json').read_text(encoding='utf-8'))
    path = UI/f'batch_{i}_ko.json'
    ko = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    bad = []
    for u, v in src.items():
        if u not in ko: bad.append(f'{u}: missing'); continue
        t = ko[u]
        if ctrl(v['ja']) != ctrl(t): bad.append(f'{u}: control tokens differ {ctrl(v["ja"])} vs {ctrl(t)}')
        if names(v['ja']) != len(re.findall(r'\{NAME:\d+:[^{}]*\}', t)): bad.append(f'{u}: name tokens differ')
        if v['ja'].count('{PAGE}') != t.count('{PAGE}'): bad.append(f'{u}: {{PAGE}} count differs')
        if JP.search(re.sub(r'\{[^{}]*\}', '', t)): bad.append(f'{u}: Japanese left')
    extra = set(ko) - set(src)
    if extra: bad.append(f'extra ids: {sorted(extra)[:10]}')
    print(f'{len(ko)}/{len(src)} translated; {len(bad)} problems')
    for b in bad[:40]: print(' ', b)

if __name__ == '__main__':
    main(sys.argv[1])
