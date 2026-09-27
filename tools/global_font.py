"""Global font (0000 pack 0 entry 65) Hangul allocation.

extend(font, chars, free_codes):
  * up to 973 glyphs are appended after the 2099 original ones (build_patch.extend_font,
    verified in game);
  * the rest are painted into Japanese glyph cells whose codes (free_codes) are no longer
    used by any untranslated message.  Only the 4x4 BC7 blocks covering those cells are
    re-encoded, in both mip levels.
Returns (new_font_bytes, {char: code}).
"""
import struct, io
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from mcdlib import parse_mcd
from render import aif_alpha
from bc7enc import encode_bc7_white_alpha4
import build_patch as bp

APPEND_MAX = 973
PITCH = 64

def _tile(ch, font):
    tile = Image.new('L', (PITCH, PITCH)); draw = ImageDraw.Draw(tile)
    box = draw.textbbox((0, 0), ch, font=font)
    draw.text(((PITCH-box[2]+box[0])//2-box[0], (PITCH-box[3]+box[1])//2-box[1]), ch, font=font, fill=255)
    return tile

def _write_blocks(d, pixels_at, iw, region, x0, y0):
    """Encode `region` (numpy alpha, 4-aligned) at (x0,y0) of an iw-wide BC7 image."""
    blob = encode_bc7_white_alpha4(region)
    bw = region.shape[1] // 4; bpr = iw // 4
    for r in range(region.shape[0] // 4):
        src = blob[r*bw*16:(r+1)*bw*16]
        dst = pixels_at + (((y0//4) + r) * bpr + x0//4) * 16
        d[dst:dst+len(src)] = src

def extend(font, chars, free_codes):
    chars = list(chars)
    head, tail = chars[:APPEND_MAX], chars[APPEND_MAX:]
    if len(tail) > len(free_codes):
        raise SystemExit(f'global font: {len(chars)} Hangul needed, capacity {APPEND_MAX + len(free_codes)}')
    data, mapping = bp.extend_font(font, head)
    if not tail: return data, mapping
    d = bytearray(data); m = parse_mcd(d)
    atlas, W, H, images, pixels = aif_alpha(d, m['imgoff'])
    # only full-width cells can hold a 64px Hangul tile without touching neighbours
    def wide(code):
        _, _, u0, v0, u1, v1 = struct.unpack_from('<II4f', d, m['sect'][4] + (code-1)*24)
        return round((u1-u0)*W) >= PITCH and round((v1-v0)*H) >= PITCH
    free_codes = [c for c in free_codes if wide(c)]
    if len(tail) > len(free_codes):
        raise SystemExit(f'global font: {len(chars)} Hangul needed, wide free cells only {len(free_codes)}')
    a = np.array(atlas, dtype=np.uint8)
    face = ImageFont.truetype(str(bp.GAME/'NanumSquareNeo-cBd.ttf'), 64)
    touched = []
    for ch, code in zip(tail, sorted(free_codes)):
        o = m['sect'][4] + (code-1)*24
        adv, _, u0, v0, u1, v1 = struct.unpack_from('<II4f', d, o)
        x0, y0 = round(u0*W), round(v0*H); x1, y1 = round(u1*W), round(v1*H)
        a[y0:y1, x0:x1] = 0
        t = np.array(_tile(ch, face))
        h = min(PITCH, H-y0); w = min(PITCH, W-x0)
        a[y0:y0+h, x0:x0+w] = np.maximum(a[y0:y0+h, x0:x0+w], t[:h, :w])
        struct.pack_into('<II4f', d, o, 72, 0, x0/W, y0/H, (x0+PITCH)/W, (y0+PITCH)/H)
        mapping[ch] = code
        touched.append((x0, y0, max(x1, x0+PITCH), max(y1, y0+PITCH)))
    # re-encode only touched blocks, mip 0 and mip 1
    pos = pixels
    for level, (iw, ih, size) in enumerate(images):
        s = W // iw
        img = a if s == 1 else np.array(Image.fromarray(a).resize((iw, ih), Image.Resampling.LANCZOS))
        for x0, y0, x1, y1 in touched:
            bx0 = (x0//s)//4*4; by0 = (y0//s)//4*4
            bx1 = min(iw, -(-(x1//s + 1)//4)*4); by1 = min(ih, -(-(y1//s + 1)//4)*4)
            _write_blocks(d, pos, iw, np.ascontiguousarray(img[by0:by1, bx0:bx1]), bx0, by0)
        pos += size
    return bytes(d), mapping
