"""Render translated global-font messages with the BUILT global font.

  python tools/preview_ui.py 0000_5_0 12770 12778 ...   -> localization/check/ui_preview.png
"""
import sys, io, struct, json
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT))
from verify_slz import decode_native_slz
from mcdlib import parse_mcd
from render import aif_alpha, dds_bc7
from localization.codec import messages

def load_font():
    d = decode_native_slz((ROOT/'reloc_build/p0_e65.slz').read_bytes())[0]
    m = parse_mcd(d); _, W, H, imgs, pos = aif_alpha(d, m['imgoff'])
    rgba = Image.open(io.BytesIO(dds_bc7(d[pos:pos+imgs[0][2]], W, H))).convert('RGBA')
    n = sum(struct.unpack_from('<I', d, m['sect'][0]+16*i)[0] for i in range(m['cnt'][0]))
    return rgba, W, H, [struct.unpack_from('<II4f', d, m['sect'][4]+24*i) for i in range(n)]

def main(key, ids):
    rgba, W, H, glyphs = load_font()
    arc, pi, ei = key.split('_')
    name = f'p{pi}_e{ei}.slz' if arc == '0000' else f'a1_p{pi}_e{ei}.slz'
    data = decode_native_slz((ROOT/'reloc_build'/name).read_bytes())[0]
    msgs = messages(data)
    out = Image.new('RGB', (1800, 120*len(ids)), (20, 25, 35))
    for row, mid in enumerate(ids):
        raw = msgs[mid]; x, y = 10, row*120; i = 0
        while i < len(raw) and raw[i]:
            b = raw[i]
            if b < 128: n = b; i += 1
            else: n = (b & 127) | (raw[i+1] << 7); i += 2
            if n >= 0x4000:
                if n == 0x4000: x = 10; y += 40
                continue
            if n > len(glyphs): x += 20; continue
            a, _, u0, v0, u1, v1 = glyphs[n-1]
            t = rgba.crop((round(u0*W), round(v0*H), round(u1*W), round(v1*H)))
            t = t.resize((max(1, t.width//2), max(1, t.height//2)))
            out.paste(t, (x, y), t); x += a//2
    out.save(ROOT/'localization/check/ui_preview.png'); print(ROOT/'localization/check/ui_preview.png')

if __name__ == '__main__':
    main(sys.argv[1], [int(x) for x in sys.argv[2:]])
