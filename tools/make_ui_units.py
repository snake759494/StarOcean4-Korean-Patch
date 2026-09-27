"""Group untranslated global-font messages (id 9/30, both archives) into unique
translation units and split them into agent batches.

  python tools/make_ui_units.py 8   -> localization/ui/units.json, localization/ui/batch_<i>.json
Translators write localization/ui/batch_<i>_ko.json  {unit_id: korean}.
"""
import sys, json, re, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
UI = ROOT/'localization/ui'; UI.mkdir(exist_ok=True)
JP = re.compile(r'[぀-ヿ一-鿿々]')

def main(nbatch):
    import build_patch as bp
    done = {(f"0000_{k.replace(':', '_')}", mid) for k, tr in bp.TRANSLATIONS.items() for mid in tr}
    inv = {r['key']: r for r in json.loads((ROOT/'localization/inventory.json').read_text(encoding='utf-8'))}
    units = {}
    for f in sorted(glob.glob(str(ROOT/'localization/source/*.json'))):
        key = Path(f).stem; r = inv.get(key)
        if not r or r['language'] != 'ja' or r['id'] not in (9, 30): continue
        tx = json.loads((ROOT/'localization/ja_text'/f'{key}.json').read_text(encoding='utf-8'))
        for row in json.loads(Path(f).read_text(encoding='utf-8')):
            if (key, row['id']) in done: continue
            ja = tx[str(row['id'])]['ja']
            if not JP.search(ja): continue          # digits / symbols only: leave as is
            local = any(int(g) > 3072 for g in re.findall(r'\{G:(\d+)\}', row['source']))
            uk = (row['raw'], key if local else '')
            u = units.setdefault(uk, {'ja': ja, 'en': tx[str(row['id'])]['en'], 'refs': []})
            u['refs'].append([key, row['id']])
    items = sorted(units.values(), key=lambda u: (u['refs'][0][0], u['refs'][0][1]))
    for i, u in enumerate(items): u['u'] = i
    (UI/'units.json').write_text(json.dumps(items, ensure_ascii=False, indent=0), encoding='utf-8')
    # contiguous batches (keeps a resource's lines together for context), balanced by characters
    total = sum(len(u['ja']) for u in items); per = total / nbatch
    b, acc, cur = 0, 0, {}
    for u in items:
        cur[u['u']] = {'ja': u['ja'], 'en': u['en'], 'where': u['refs'][0][0]}
        acc += len(u['ja'])
        if acc >= per * (b + 1) and b < nbatch - 1:
            (UI/f'batch_{b}.json').write_text(json.dumps(cur, ensure_ascii=False, indent=0), encoding='utf-8'); b += 1; cur = {}
    (UI/f'batch_{b}.json').write_text(json.dumps(cur, ensure_ascii=False, indent=0), encoding='utf-8')
    print(len(items), 'units,', total, 'JP chars')

if __name__ == '__main__':
    main(int(sys.argv[1]))
