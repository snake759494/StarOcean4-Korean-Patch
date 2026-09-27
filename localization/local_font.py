"""Rebuild a fully translated scene resource's own font.

The atlas keeps its width; when the Korean glyph set does not fit, the texture
HEIGHT is doubled (header fields patched the same way as the global font,
which is known to work in game).  aif_resize() is also used for the id=59
companion image so both stay identical.
"""
import struct, io, math, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from mcdlib import parse_mcd
from render import aif_alpha, dds_bc7
from bc7enc import encode_bc7_alpha, encode_bc7_white_alpha4
from localization.codec import encode, literal_chars

BASE = 29          # baseline inside a 40px cell (fits '(' and ')' of NanumSquare Neo 34px)
CELL_H = 38

def aif_resize(buf, aif, new_h):
    """Return buf with the AIF at offset `aif` resized to height new_h (pixels zeroed)."""
    d = bytearray(buf)
    pos = aif + 0x10; descs = []; amf = None
    while True:
        tag = bytes(d[pos:pos+4]); size = struct.unpack_from('<I', d, pos+4)[0]
        if tag == b'Xgmi': descs.append(pos)
        if tag == b' FMA': amf = pos; break
        pos += size
    old = []
    for desc in descs:
        w = struct.unpack_from('<H', d, desc+0x28)[0]; h = struct.unpack_from('<H', d, desc+0x2a)[0]
        old.append((w, h, struct.unpack_from('<I', d, desc+0x3c)[0]))
    H0 = old[0][1]; sizes = []
    for desc, (w, h, ds) in zip(descs, old):
        nh = h * new_h // H0; ns = ds * nh // h; sizes.append(ns)
        struct.pack_into('<H', d, desc+0x2a, nh); struct.pack_into('<I', d, desc+0x38, nh); struct.pack_into('<I', d, desc+0x3c, ns)
    pix = amf + 0x1d0
    tail = bytes(d[pix+sum(ds for *_, ds in old):])
    struct.pack_into('<I', d, amf+4, 0x1d0 + sum(sizes))
    struct.pack_into('<I', d, amf+0x60, sum(sizes))
    struct.pack_into('<I', d, amf+0xb0, sizes[0])
    if len(sizes) > 1:
        struct.pack_into('<I', d, amf+0x110, sizes[1]); struct.pack_into('<I', d, amf+0x118, sizes[0])
    return bytes(d[:pix]) + bytes(sum(sizes)) + tail

def rebuild(data, translations, font_path, preview_path, compact=False):
    d = bytearray(data); m = parse_mcd(d); sections = m['sect']
    assert m['cnt'][0] == 1
    assert set(translations) == {mid for mid, _ in m['msgs']}, 'Local font replacement requires every message'
    chars = sorted({c for s in translations.values() for c in literal_chars(s) if c != '\n'})
    mapping = {c: i+1 for i, c in enumerate(chars)}
    _, width, height, images, pixels = aif_alpha(d, m['imgoff'])
    font = ImageFont.truetype(str(font_path), 34)
    tile_width = max(math.ceil(font.getlength(c)) + 2 for c in chars)
    pitch_y = 40; columns = width // tile_width
    need = math.ceil(len(chars) / columns) * pitch_y
    new_h = height
    while need > new_h: new_h *= 2
    assert new_h <= 4096, 'Local atlas capacity exceeded even at 4096px'
    pool = bytearray()
    for i, (mid, _) in enumerate(m['msgs']):
        struct.pack_into('<I', d, sections[2]+8*i+4, len(pool))
        pool += encode(translations[mid], mapping)
    glyph_start = (sections[3] + len(pool) + 15) & ~15
    texpos = (glyph_start + 24*len(chars) + 15) & ~15
    if texpos + 16 > sections[6]:
        growth = (texpos + 16 - sections[6] + 4095) & ~4095
        d[sections[6]:sections[6]] = bytes(growth)
        sections = list(sections); sections[6] += growth; pixels += growth
        struct.pack_into('<I', d, 0x18+6*4, sections[6])
        for field in (4, 12, 20):
            old = struct.unpack_from('<I', d, field)[0]
            if old: struct.pack_into('<I', d, field, old + growth)
    d[sections[3]:sections[6]] = bytes(sections[6] - sections[3])
    d[sections[3]:sections[3]+len(pool)] = pool
    struct.pack_into('<I', d, sections[0], len(chars))
    struct.pack_into('<II', d, 0x28, glyph_start, texpos)
    if new_h != height:
        d = bytearray(aif_resize(bytes(d), sections[6], new_h))
        struct.pack_into('<I', d, 0x14, len(d))
        _, width, height, images, pixels = aif_alpha(d, sections[6])
        assert height == new_h
    struct.pack_into('<4I', d, texpos, width, height, 0, 0)
    atlas = Image.new('L', (width, height)); draw = ImageDraw.Draw(atlas)
    for i, ch in enumerate(chars):
        x = (i % columns) * tile_width; y = (i // columns) * pitch_y
        advance = math.ceil(font.getlength(ch)); gw = advance + 2
        tile = Image.new('L', (gw, pitch_y)); td = ImageDraw.Draw(tile)
        td.text((1, BASE), ch, font=font, anchor='ls', fill=255)
        atlas.paste(tile.crop((0, 0, gw, CELL_H)), (x, y))
        struct.pack_into('<II4f', d, glyph_start+24*i, advance, 0, x/width, y/height, (x+gw)/width, (y+CELL_H)/height)
    pos = pixels
    for iw, ih, size in images:
        source = atlas if (iw, ih) == (width, height) else atlas.resize((iw, ih), Image.Resampling.LANCZOS)
        texture = encode_bc7_white_alpha4(np.array(source)) if compact else encode_bc7_alpha(np.array(source), rgb=255)
        assert len(texture) == size
        d[pos:pos+size] = texture; pos += size
    assert struct.unpack_from('<I', d, 0x14)[0] == len(d)
    rgba = Image.open(io.BytesIO(dds_bc7(d[pixels:pixels+images[0][2]], width, height))).convert('RGBA')
    preview = Image.new('RGB', (1200, len(translations)*100), (20, 25, 35))
    for line, (mid, text) in enumerate(translations.items()):
        x = 35; y = line*100
        ImageDraw.Draw(preview).text((2, y), str(mid), fill='white')
        display = re.sub(r'\{NAME:\d+:([^{}]*)\}', r'\1', text).replace('{PAGE}', '\n')
        display = re.sub(r'\{RAW:[0-9a-fA-F]+\}', '', display)
        for ch in display:
            if ch == '\n': x = 35; y += 40; continue
            advance, _, u, v, r, b = struct.unpack_from('<II4f', d, glyph_start+24*(mapping[ch]-1))
            tile = rgba.crop((round(u*width), round(v*height), round(r*width), round(b*height)))
            if x + tile.width < 1200: preview.paste(tile, (x, y), tile)
            x += advance
    preview.save(preview_path)
    return bytes(d), mapping
