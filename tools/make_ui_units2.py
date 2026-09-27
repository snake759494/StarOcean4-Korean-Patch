"""Supplementary units: messages whose text was hidden inside a control token
(0x88 help-window / 0x94) by the old decoder.  Does NOT renumber units.json.

  python tools/make_ui_units2.py  -> localization/ui/units2.json, localization/ui/batch_s.json
"""
import sys, json, re, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT))
from localization.codec import decode, LATIN
import transcribe_ui as T

JP = re.compile(r'[぀-ヿ一-鿿々]')

def main():
    inv = {r['key']: r for r in json.loads((ROOT/'localization/inventory.json').read_text(encoding='utf-8'))}
    units = {}
    for f in sorted(glob.glob(str(ROOT/'localization/source/*.json'))):
        key = Path(f).stem; r = inv.get(key)
        if not r or r['language'] != 'ja' or r['id'] not in (9, 30): continue
        rows = json.loads(Path(f).read_text(encoding='utf-8'))
        todo = [row for row in rows if re.search(r'\{RAW:(8880|9480)[0-9a-f]{10,}\}', row['source'])]
        if not todo: continue
        lmap = None
        for row in todo:
            src = decode(bytes.fromhex(row['raw']), local=True)
            codes = [int(g) for g in re.findall(r'\{G:(\d+)\}', src)]
            if lmap is None and any(c > 3072 for c in codes): lmap = T.local_map(key)
            def sub(m):
                n = int(m.group(1))
                if n <= 1888: return T.GMAP.get(n, '□')
                if n <= 2099: return LATIN.get(n, '□')
                return (lmap or {}).get(n - 3072, '■')
            ja = re.sub(r'\{G:(\d+)\}', sub, src)
            if not JP.search(re.sub(r'\{RAW:[^}]*\}', '', ja)): continue
            local = any(c > 3072 for c in codes)
            u = units.setdefault((row['raw'], key if local else ''), {'ja': ja, 'en': row.get('english_visual_reference', '') or '', 'refs': []})
            u['refs'].append([key, row['id']])
    items = list(units.values())
    for i, u in enumerate(items): u['u'] = f's{i}'
    (ROOT/'localization/ui/units2.json').write_text(json.dumps(items, ensure_ascii=False, indent=0), encoding='utf-8')
    (ROOT/'localization/ui/batch_s.json').write_text(json.dumps({u['u']: {'ja': u['ja'], 'en': u['en'], 'where': u['refs'][0][0]} for u in items}, ensure_ascii=False, indent=0), encoding='utf-8')
    print(len(items), 'supplementary units')

if __name__ == '__main__':
    main()
