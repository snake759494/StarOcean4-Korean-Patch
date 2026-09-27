"""Transcribe Japanese global-font text resources (id 9/30) to readable text.

codes 1..1888  -> global JP bank (OCR map localization/global_charmap.json)
codes 1889..2099 -> global Latin bank (codec.LATIN)
codes >= 3073  -> the resource's own embedded font, glyph index = code-3072 (OCR per resource)
Output: localization/ja_text/<key>.json  {id: {"ja": text, "en": english_ref or ""}}
"""
import sys, json, re, glob, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT))
from localization.codec import LATIN
import glyph_ocr

OUTD = ROOT/'localization/ja_text'; OUTD.mkdir(exist_ok=True)
GMAP = {int(k): v['c'] for k, v in json.loads((ROOT/'localization/global_charmap.json').read_text(encoding='utf-8')).items()}
_chars = None

def local_map(key):
    global _chars
    import build_reloc as br
    arc, pi, ei = key.split('_')
    _, data = br.read_original(int(pi), int(ei), int(arc))
    try:
        imgs = glyph_ocr.glyph_images(data)
    except Exception:
        return {}
    _chars = _chars or glyph_ocr.candidates()
    return {k: v['c'] for k, v in glyph_ocr.identify(imgs, _chars).items()}

def main():
    inv = {r['key']: r for r in json.loads((ROOT/'localization/inventory.json').read_text(encoding='utf-8'))}
    for f in sorted(glob.glob(str(ROOT/'localization/source/*.json'))):
        key = Path(f).stem; r = inv.get(key)
        if (OUTD/f'{key}.json').exists(): continue
        if not r or r['language'] != 'ja' or r['id'] not in (9, 30): continue
        rows = json.loads(Path(f).read_text(encoding='utf-8'))
        needs_local = any(int(g) > 3072 for row in rows for g in re.findall(r'\{G:(\d+)\}', row['source']))
        lmap = local_map(key) if needs_local else {}
        en = {}
        ref = r.get('english_reference') if 'english_reference' in r else None
        out = {}
        for row in rows:
            def sub(m):
                n = int(m.group(1))
                if n <= 1888: return GMAP.get(n, '□')
                if n <= 2099: return LATIN.get(n, '□')
                if n > 3072: return lmap.get(n - 3072, '■')
                return '□'
            out[row['id']] = {'ja': re.sub(r'\{G:(\d+)\}', sub, row['source']),
                              'en': row.get('english_visual_reference', '') or ''}
        (OUTD/f'{key}.json').write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
        print(key, len(out), 'local' if needs_local else '')

if __name__ == '__main__':
    main()
