"""Identify glyph bitmaps of an MCD font by template matching against
Japanese system fonts.  Produces {glyph_index(1-based): char} with scores.

  python tools/glyph_ocr.py global          -> localization/global_charmap.json
"""
import sys, io, json, struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT))
from mcdlib import parse_mcd
from render import aif_alpha, dds_bc7
S = 32
FONTS = [r'C:\Windows\Fonts\YuGothB.ttc', r'C:\Windows\Fonts\BIZ-UDGothicB.ttc', r'C:\Windows\Fonts\BIZ-UDGothicR.ttc']

def candidates():
    cs = set()
    for a, b in [(0x3000, 0x30ff), (0xff01, 0xff5e), (0x2010, 0x2312), (0x25a0, 0x266f), (0x4e00, 0x9fff), (0x21, 0x7e), (0xa0, 0x17f)]:
        cs.update(chr(c) for c in range(a, b + 1))
    # restrict kanji to JIS X 0208 (encodable in cp932)
    out = []
    for c in sorted(cs):
        try: c.encode('cp932')
        except UnicodeEncodeError: continue
        out.append(c)
    return out

def norm(img):
    """alpha image -> tight bbox -> SxS float vector (keeps aspect)."""
    a = np.asarray(img, dtype=np.float32)
    ys, xs = np.nonzero(a > 40)
    if len(xs) == 0: return None
    a = a[ys.min():ys.max()+1, xs.min():xs.max()+1]
    h, w = a.shape; m = max(h, w)
    pad = np.zeros((m, m), np.float32); pad[(m-h)//2:(m-h)//2+h, (m-w)//2:(m-w)//2+w] = a
    v = np.asarray(Image.fromarray(pad.astype(np.uint8)).resize((S, S), Image.Resampling.LANCZOS), np.float32).ravel()
    v -= v.mean(); n = np.linalg.norm(v)
    return v / n if n else None

def glyph_images(data):
    m = parse_mcd(data); _, w, h, imgs, pos = aif_alpha(data, m['imgoff'])
    rgba = Image.open(io.BytesIO(dds_bc7(data[pos:pos+imgs[0][2]], w, h))).convert('RGBA').getchannel('A')
    count = sum(struct.unpack_from('<I', data, m['sect'][0]+16*i)[0] for i in range(m['cnt'][0]))
    out = []
    for i in range(count):
        adv, _, u0, v0, u1, v1 = struct.unpack_from('<II4f', data, m['sect'][4] + 24*i)
        out.append(rgba.crop((round(u0*w), round(v0*h), round(u1*w), round(v1*h))))
    return out

def reference(chars):
    mats = []
    for fp in FONTS:
        font = ImageFont.truetype(fp, 64)
        rows = []
        for c in chars:
            im = Image.new('L', (96, 96)); ImageDraw.Draw(im).text((8, 8), c, font=font, fill=255)
            v = norm(im); rows.append(v if v is not None else np.zeros(S*S, np.float32))
        mats.append(np.stack(rows))
    return mats

_REF = {}
def identify(images, chars=None):
    chars = chars or candidates()
    key = len(chars)
    if key not in _REF: _REF[key] = reference(chars)
    refs = _REF[key]
    vecs = [norm(im) for im in images]
    G = np.stack([v if v is not None else np.zeros(S*S, np.float32) for v in vecs])
    score = np.max(np.stack([G @ R.T for R in refs]), axis=0)
    best = score.argmax(1); top = score.max(1)
    second = np.sort(score, 1)[:, -2]
    res = {}
    for i, v in enumerate(vecs):
        if v is None: res[i+1] = {'c': ' ', 's': 1.0, 'm': 1.0}
        else: res[i+1] = {'c': chars[best[i]], 's': float(top[i]), 'm': float(top[i]-second[i])}
    return res

if __name__ == '__main__':
    from verify_slz import decode_native_slz
    data = decode_native_slz((ROOT/'build/p0_e65.original.bin').read_bytes())[0]
    res = identify(glyph_images(data))
    (ROOT/'localization/global_charmap.json').write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding='utf-8')
    low = [(k, v['c'], round(v['s'], 2)) for k, v in res.items() if v['s'] < 0.8]
    print(len(res), 'glyphs; low-confidence:', len(low)); print(low[:60])
    print(''.join(res[i]['c'] for i in range(1, 400)))
