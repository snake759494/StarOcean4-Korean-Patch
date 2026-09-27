"""Relocate KCAP packs in 0000.bin by rewriting the encrypted Aska TOC.

TOC = first 0xC0000 bytes of 0000.bin, XOR-encrypted in 12-byte steps
(exe RVA 0x4a88a0, seed 0x13578642; loader RVA 0x3e3fa0).
Pack records start at +0x6c: (u32 sectors, u32 bytes, u32 start_sector),
sector = 0x800, start bit 28 selects 0001.bin. The game locates packs only
through this table, so a pack can be moved to the end of the archive and grown.
"""
import struct, os, json, hashlib
from aska_toc import crypt12
TOC_SIZE = 0xC0000
REC_BASE = 0x6c
SECTOR = 0x800

def read_toc(f):
    f.seek(0); return bytearray(crypt12(f.read(TOC_SIZE)))

def records(toc):
    out = []; o = REC_BASE
    while True:
        n, b, s = struct.unpack_from('<3I', toc, o)
        if n == 0 and b == 0 and s == 0: break
        out.append((o, n, b, s)); o += 12
    return out

def find_record(toc, pack_offset):
    hits = [r for r in records(toc) if r[3] == pack_offset // SECTOR]
    assert len(hits) == 1, (pack_offset, hits)
    return hits[0]

def append_pack(f, toc, old_offset, pack_bytes):
    """Write pack_bytes at EOF (sector aligned) and repoint the TOC record."""
    o, n, b, s = find_record(toc, old_offset)
    f.seek(0, 2); end = f.tell()
    start = (end + SECTOR - 1) // SECTOR * SECTOR
    size = (len(pack_bytes) + SECTOR - 1) // SECTOR * SECTOR
    f.write(bytes(start - end)); f.write(pack_bytes); f.write(bytes(size - len(pack_bytes)))
    struct.pack_into('<3I', toc, o, size // SECTOR, size, start // SECTOR)
    return start

def write_toc(f, toc):
    f.seek(0); f.write(crypt12(bytes(toc)))

def build_pack(orig_pack, replacements, alias=None):
    """replacements: {entry_index: (compressed_bytes, decoded_size)} -> new pack bytes.
    Entries keep their original ORDER (streamed loaders read them sequentially);
    everything after a grown entry is shifted, 16-byte aligned."""
    src = bytes(orig_pack); assert src[:4] == b'KCAP'
    cnt, total = struct.unpack_from('<II', src, 8)
    ents = [list(struct.unpack_from('<HHIII', src, 16 + i*16)) for i in range(cnt)]
    order = sorted(range(cnt), key=lambda i: ents[i][4])
    spans = {i: (ents[order[k+1]][4] if k+1 < cnt else total) - ents[i][4] for k, i in enumerate(order)}
    if not alias and all(len(b) <= spans[i] for i, (b, _) in replacements.items()):
        # stable layout: every entry stays at its original offset (minimal byte changes)
        out = bytearray(src)
        for i, (blob, usize) in replacements.items():
            o = ents[i][4]
            out[o:o+spans[i]] = blob + bytes(spans[i] - len(blob))
            struct.pack_into('<I', out, 16 + i*16 + 8, usize)
        return bytes(out)
    head = bytearray(src[:ents[order[0]][4]])
    body = bytearray(); pos = len(head)
    alias = alias or {}
    for k, i in enumerate(order):
        start = ents[i][4]
        end = ents[order[k+1]][4] if k+1 < cnt else total
        if i in alias: continue            # shares another entry's data (set below)
        if i in replacements:
            blob, usize = replacements[i]; ents[i][3] = usize
        else:
            blob = src[start:end]
            if blob[:3] == b'SLZ':   # drop slack after the compressed stream
                blob = blob[:32 + struct.unpack_from('<I', blob, 8)[0]]
        ents[i][4] = pos
        pad = (-len(blob)) % 16
        body += blob + bytes(pad); pos += len(blob) + pad
    for i, j in alias.items():
        ents[i][3] = ents[j][3]; ents[i][4] = ents[j][4]
    for i, e in enumerate(ents): struct.pack_into('<HHIII', head, 16 + i*16, *e)
    out = bytes(head) + bytes(body)
    out = bytearray(out); struct.pack_into('<I', out, 12, len(out))
    return bytes(out)
