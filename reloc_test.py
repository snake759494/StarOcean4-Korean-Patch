"""Decisive runtime test: move pack 15 to EOF with one visibly changed string."""
import sys, json, struct, hashlib, subprocess, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT))
from slz import slz_decompress
from slzenc import slz_compress_v3
from verify_slz import decode_native_v3
from aska_reloc import read_toc, find_record, append_pack, write_toc, build_pack, TOC_SIZE
from build_patch import replace_messages
GAME = Path(r'C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster')
ARC = GAME/'0000.bin'; OUT = ROOT/'reloc'
P = json.loads((ROOT/'tools/packs0.json').read_text())
mapping = json.loads((ROOT/'build/manifest.json').read_text(encoding='utf-8'))['glyph_mapping']
TEXT = '재배치 시험 성공: 이 문장이 보이면 확장이 가능합니다.'

def main(action):
    if b'StarOceanTheLastHope.exe' in subprocess.check_output(['tasklist','/FI','IMAGENAME eq StarOceanTheLastHope.exe','/NH']):
        raise SystemExit('Game is running')
    if action == 'restore':
        meta = json.loads((OUT/'backup.json').read_text())
        with ARC.open('r+b') as f:
            f.seek(0); f.write((OUT/'toc_original.bin').read_bytes()); f.truncate(meta['size'])
        print('restored TOC and size', meta['size']); return
    p = P[15]; ei = 1
    with ARC.open('rb') as f:
        f.seek(p['off']); pack = f.read(p['tot'])
        raw_toc = (f.seek(0), f.read(TOC_SIZE))[1]
        toc = read_toc(f)
    size = ARC.stat().st_size
    if not (OUT/'backup.json').exists():
        OUT.mkdir(exist_ok=True)
        (OUT/'toc_original.bin').write_bytes(raw_toc)
        (OUT/'backup.json').write_text(json.dumps({'size': size, 'toc_sha256': hashlib.sha256(raw_toc).hexdigest()}))
    e = struct.unpack_from('<HHIII', pack, 16 + ei*16)
    comp = pack[e[4]:]
    dec = decode_native_v3(comp)[0] if comp[3] == 3 else slz_decompress(comp)[0]
    assert len(dec) == e[3]
    new = replace_messages(dec, {0x4e95: TEXT}, mapping)
    blob = slz_compress_v3(new, template=comp[:32])
    assert decode_native_v3(blob)[0] == new
    newpack = build_pack(pack, {ei: (blob, len(new))})
    rec = find_record(toc, p['off'])
    with ARC.open('r+b') as f:
        start = append_pack(f, toc, p['off'], newpack)
        write_toc(f, toc)
    with ARC.open('rb') as f:
        t2 = read_toc(f); r2 = find_record(t2, start)
    print('record', rec, '->', r2, 'new pack at', hex(start), 'size', len(newpack))

if __name__ == '__main__': main(sys.argv[1] if len(sys.argv) > 1 else 'apply')
