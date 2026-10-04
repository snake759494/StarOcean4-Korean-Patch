"""Validate localization/story_<ref>_ko.py against every JP copy of the scene
and render a preview of the rebuilt Korean font.

  python tools/check_story.py 65747          -> prints OK/problems, writes localization/check/preview_<ref>.png
  python tools/check_story.py render 65747   -> renders the Japanese pages to localization/check/ja_<ref>_<page>.png
"""
import sys, json, importlib, subprocess, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT))
CHK = ROOT/'localization/check'; CHK.mkdir(exist_ok=True)

def scenes():
    inv = json.loads((ROOT/'localization/inventory.json').read_text(encoding='utf-8'))
    out = {}
    for r in inv:
        if r['id'] == 58 and r['language'] == 'ja': out.setdefault(r['ref'], []).append(r)
    return out

def render(ref):
    r = scenes()[ref][0]
    subprocess.run([sys.executable, str(ROOT/'localization/render_story.py'), r['key']], check=True)
    for p in sorted((ROOT/'localization').glob(f"story_{r['key']}_*.png")):
        target = CHK/f"ja_{ref}_{p.stem.split('_')[-1]}.png"
        p.replace(target); print(target)

def check(ref):
    import build_reloc as br
    from mcdlib import parse_mcd
    K = importlib.import_module(f'localization.story_{ref}_ko').K
    problems = []
    for r in scenes()[ref]:
        _, data = br.read_original(r['pack'], r['entry'], int(r['archive']))
        ids = {mid for mid, _ in parse_mcd(data)['msgs']}
        if ids != set(K):
            problems.append(f"{r['key']}: missing {sorted(ids-set(K))} extra {sorted(set(K)-ids)}")
    for mid, s in K.items():
        if s == '': problems.append(f'{mid}: empty message stalls the event; keep at least a space')
        if '{RAW:9080' in s: problems.append(f'{mid}: ruby token (9080) holds Japanese glyph indices; drop it')
        s = re.sub(r'\{NAME:\d+:([^{}]*)\}', r'\1', s); s = re.sub(r'\{RAW:[0-9a-fA-F]+\}', '', s)
        for line in s.replace('{PAGE}', '\n').split('\n'):
            if len(line) > 34: problems.append(f'{mid}: long line ({len(line)}): {line}')
    if not problems:
        r = scenes()[ref][0]
        _, data = br.read_original(r['pack'], r['entry'], int(r['archive']))
        try:
            br.rebuild_local_font(data, K, br.FONT, CHK/f'preview_{ref}.png', compact=True)
        except AssertionError as e:
            problems.append(f'rebuild failed: {e}')
    print('OK' if not problems else '\n'.join(problems))
    if not problems: print(CHK/f'preview_{ref}.png')

if __name__ == '__main__':
    if sys.argv[1] == 'render': render(int(sys.argv[2]))
    else: check(int(sys.argv[1]))
