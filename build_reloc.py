"""Relocation build for both archives.  Patched packs (or the multi-pack TOC
blocks that contain them) are rewritten at the END of 0000.bin / 0001.bin and
the encrypted Aska TOC (0000.bin head) is repointed.  Original bytes are never
edited in place.  See AGENTS.md for the rules this enforces.

  python build_reloc.py build     -> reloc_build/ (packs + manifest), archives untouched
  python build_reloc.py apply     -> restore pristine TOC/sizes, append, write TOC
  python build_reloc.py restore   -> pristine TOC + original file sizes
"""
import sys, json, struct, hashlib, subprocess, os, importlib, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT))
import build_patch as bp
from slz import slz_decompress
from slzenc import slz_compress, slz_compress_v3
from verify_slz import decode_native_slz
from aska_reloc import read_toc, write_toc, build_pack
from mcdlib import parse_mcd
from localization.local_font import rebuild as rebuild_local_font
from render import aif_alpha

GAME = bp.GAME
ARCS = {0: GAME/'0000.bin', 1: GAME/'0001.bin'}
OUT = ROOT/'reloc_build'; STATE = ROOT/'reloc'
PACKSA = {0: json.loads((ROOT/'tools/packs0.json').read_text()),
          1: json.loads((ROOT/'tools/packs.json').read_text())}
bp.PACKS = PACKSA[0]
FONT = GAME/'NanumSquareNeo-cBd.ttf'
sha = lambda b: hashlib.sha256(b).hexdigest()

def game_running():
    return b'StarOceanTheLastHope.exe' in subprocess.check_output(
        ['tasklist', '/FI', 'IMAGENAME eq StarOceanTheLastHope.exe', '/NH'], creationflags=0x08000000)

def pristine():
    meta = json.loads((STATE/'backup.json').read_text())
    toc = (STATE/'toc_original.bin').read_bytes()
    assert sha(toc) == meta['toc_sha256']
    return meta['size'], toc

def restore():
    if game_running(): raise SystemExit('Close the game first.')
    size, toc = pristine()
    with ARCS[0].open('r+b') as f:
        f.seek(0); f.write(toc); f.truncate(size); f.flush(); os.fsync(f.fileno())
    size1 = json.loads((STATE/'backup1.json').read_text())['size']
    with ARCS[1].open('r+b') as f:
        f.truncate(size1); f.flush(); os.fsync(f.fileno())

def read_original(pi, ei, arc=0):
    """Original compressed + decoded bytes from the pristine layout."""
    p = PACKSA[arc][pi]; e = p['e'][ei]
    backup = ROOT/'build'/f'p{pi}_e{ei}.original.bin'   # spans once overwritten in place
    if arc == 0 and backup.exists():
        raw = backup.read_bytes(); dec = decode_native_slz(raw)[0]
        assert len(dec) == e[3]; return raw, dec
    ends = sorted([r[4] for r in p['e'] if r[4] > e[4]] + [p['tot']])
    with ARCS[arc].open('rb') as f:
        f.seek(p['off'] + e[4]); raw = f.read(ends[0] - e[4])
    dec = decode_native_slz(raw)[0] if raw[3] in (1, 3) else slz_decompress(raw)[0]
    assert len(dec) == e[3], (arc, pi, ei)
    return raw, dec

def _chunks(buf):
    """(compressed chunk bytes incl. u16 length) per chunk of an SLZ stream"""
    pos = struct.unpack_from('<I', buf, 20)[0]; usize = struct.unpack_from('<I', buf, 12)[0]
    size = buf[25] << 10; out = []
    for start in range(0, usize, size):
        n = struct.unpack_from('<H', buf, pos)[0]
        actual = n or min(size, usize - start)
        out.append(buf[pos:pos+actual+2]); pos += actual + 2
    return out

def compress(orig, data):
    blob = slz_compress_v3(data, template=orig[:32]) if orig[3] == 3 else slz_compress(data)
    # reuse the original compressed chunk wherever the decoded 64 KiB chunk is unchanged
    if orig[3] == blob[3] and orig[25] == blob[25]:
        odec = decode_native_slz(orig)[0]; size = orig[25] << 10
        oc = _chunks(orig); nc = _chunks(blob)
        body = b''.join(o if (i < len(oc) and odec[i*size:(i+1)*size] == data[i*size:(i+1)*size] and len(o) < len(n)) else n
                        for i, (o, n) in enumerate(zip(oc + [b''] * len(nc), nc)))
        h = bytearray(blob[:32]); struct.pack_into('<I', h, 8, len(body))
        cand = bytes(h) + body
        if len(cand) < len(blob) and decode_native_slz(cand)[0] == data: blob = cand
    assert decode_native_slz(blob)[0] == data, 'round trip failed'
    return blob

def mcd_length_ok(data):
    return data[:4] != b'pDCM' or struct.unpack_from('<I', data, 0x14)[0] == len(data)

def companion(pi, ei, arc=0):
    """id=59 AIF copy of an id=58 scene font in the same pack/language."""
    ents = PACKSA[arc][pi]['e']; e = ents[ei]
    hits = [i for i, r in enumerate(ents) if r[0] == 59 and r[1] == e[1] and r[2] == e[2]]
    return hits[0] if hits else None

def sync_companion(patched_mcd, external):
    """Make the id=59 AIF identical in geometry and pixels to the MCD's embedded atlas."""
    from localization.local_font import aif_resize
    m_base = struct.unpack_from('<I', patched_mcd, 48)[0]
    _, w, h, imgs, ppix = aif_alpha(patched_mcd, m_base)
    _, ew, eh, eimgs, epix = aif_alpha(external, 0)
    if eh != h:
        external = aif_resize(external, 0, h)
        _, ew, eh, eimgs, epix = aif_alpha(external, 0)
    assert (w, h, imgs) == (ew, eh, eimgs), 'companion geometry differs'
    size = sum(s for _, _, s in imgs)
    out = bytearray(external); out[epix:epix+size] = patched_mcd[ppix:ppix+size]
    return bytes(out)

def story_translations():
    """{ref: K} from localization/story_<ref>_ko.py"""
    out = {}
    for path in sorted(glob.glob(str(ROOT/'localization/story_*_ko.py'))):
        stem = Path(path).stem
        out[int(stem.split('_')[1])] = importlib.import_module(f'localization.{stem}').K
    return out

_RECS = None
def can_grow(arc, off, slot):
    """True when the pack is the last pack of every TOC record that contains it."""
    global _RECS
    if _RECS is None:
        from aska_toc import crypt12
        _RECS = all_records(crypt12(pristine()[1]))
    inside = [(st & 0x0fffffff) * 0x800 + b for o, n, b, st in _RECS
              if (st >> 28) == arc and (st & 0x0fffffff) * 0x800 <= off < (st & 0x0fffffff) * 0x800 + b]
    return bool(inside) and all(off + slot >= end for end in inside)

def build():
    OUT.mkdir(exist_ok=True); bp.OUT = OUT
    decoded = {}; applied = {}
    import re, global_font
    inv_by_key = {r['key']: r for r in json.loads((ROOT/'localization/inventory.json').read_text(encoding='utf-8'))}
    # 1. global-font translations: Codex resources (0000) + UI units (both archives)
    gtr = {f"0000_{k.replace(':', '_')}": dict(v) for k, v in bp.TRANSLATIONS.items()}
    def _units(name):   # full units (with Japanese) locally, refs-only copy in the public repo
        p = ROOT/'localization/ui'/f'{name}.json'
        return json.loads((p if p.exists() else p.with_name(f'{name}_refs.json')).read_text(encoding='utf-8'))
    units = _units('units') + _units('units2')
    ko = {}
    for p in glob.glob(str(ROOT/'localization/ui/batch_*_ko.json')):
        ko.update(json.loads(Path(p).read_text(encoding='utf-8')))
    for u in units:
        t = ko.get(str(u['u']))
        if t is None: continue
        for key, mid in u['refs']:
            if key.startswith('0001_668_'): continue   # staff roll: keep original (OCR'd names unreliable)
            gtr.setdefault(key, {})[mid] = t
    chars = sorted({c for tr in gtr.values() for s in tr.values()
                    for c in bp.literal_chars(s) if c not in bp.ENCODING and c != '\n'})
    # JP glyph codes still needed by untranslated global-font messages
    used = set(range(1, 346))   # ASCII, symbols and all kana: save-data names use them
    for f in glob.glob(str(ROOT/'localization/source/*.json')):
        key = Path(f).stem; r = inv_by_key.get(key)
        if not r or r['language'] != 'ja' or r['id'] not in (9, 30): continue
        done = gtr.get(key, {})
        for row in json.loads(Path(f).read_text(encoding='utf-8')):
            # ruby blocks ({RAW:9080..}) are copied verbatim and keep their JP glyph codes
            # control codes whose arguments carry JP glyph codes are copied verbatim: protect them
            if row['id'] in done and not re.search(r'\{RAW:(?!9380)[0-9a-f]{13,}\}', row['source']): continue
            used.update(int(g) for g in re.findall(r'\{G:(\d+)\}', row['source']) if int(g) <= 1888)
    free = [c for c in range(151, 1889) if c not in used]
    print(f'global Hangul: {len(chars)} (append {min(len(chars), 973)}, reuse {max(0, len(chars)-973)} of {len(free)} free JP cells)', flush=True)
    # Untranslated messages still carry Japanese DEFAULT names inside name tokens
    # (e.g. a menu card that is only {NAME:1:エッジ}); the game shows that default.
    # Rewrite just the token, keep every other original glyph ({G:n}).
    from localization.codec import decode as _decode
    BASE = {1: '에지', 2: '레이미', 3: '페이즈', 4: '림르', 5: '바카스', 6: '메리클', 7: '사라', 8: '뮤리아', 9: '아르마트'}
    def kr_name(vid):
        k, n = divmod(vid, 256); b = BASE.get(n)
        if b is None: return None
        return {0: b, 1: b[:1], 2: b[:2], 3: b[:1], 4: b[:2]}.get(k, b)
    def fix_tokens(text):
        def sub(m):
            h = m.group(1); vid = int(h[2:4] + h[0:2], 16); ko = kr_name(vid)
            return f'{{NAME:{vid}:{ko}}}' if ko else m.group(0)
        return re.sub(r'\{RAW:9380([0-9a-f]{4})[0-9a-f]*?00\}', sub, text)
    renamed = 0
    for f in glob.glob(str(ROOT/'localization/source/*.json')):
        key = Path(f).stem; r = inv_by_key.get(key)
        if not r or r['language'] != 'ja' or r['id'] not in (9, 30) or key.startswith('0001_668_'): continue
        done = gtr.get(key, {})
        for row in json.loads(Path(f).read_text(encoding='utf-8')):
            if row['id'] in done or '9380' not in row['raw']: continue
            t = _decode(bytes.fromhex(row['raw']), local=True)
            t2 = fix_tokens(t)
            if t2 != t and '{RAW:9380' not in t2:
                gtr.setdefault(key, {})[row['id']] = t2; renamed += 1
    print(f'  name tokens localized in {renamed} untranslated messages', flush=True)
    _, font = read_original(0, 65)
    font2, mapping = global_font.extend(font, chars, free)
    decoded[(0, 0, 65)] = font2
    # Resources whose text is (mostly) drawn from their OWN font (codes > 0xC00) go
    # through a renderer that indexes the local glyph table directly: global Hangul
    # codes there crash the game (534:60 on entering the tutorial).  Skip them.
    for key in list(gtr):
        src = json.loads((ROOT/'localization/source'/f'{key}.json').read_text(encoding='utf-8'))
        codes = [int(g) for r in src for g in re.findall(r'\{G:(\d+)\}', r['source'])]
        if codes and sum(c > 3072 for c in codes) * 2 > len(codes):
            print(f'  local-font resource {key}: left untranslated', flush=True); del gtr[key]
    # 2. global-font message resources
    for key, tr in gtr.items():
        arc, pi, ei = map(int, key.split('_'))
        _, data = read_original(pi, ei, arc)
        decoded[(arc, pi, ei)] = bp.replace_messages(data, tr, mapping); applied[key] = len(tr)
    # 3. scene-local fonts: every JP id=58 copy of a translated scene, both archives
    inv = json.loads((ROOT/'localization/inventory.json').read_text(encoding='utf-8'))
    scenes = {}
    for r in inv:
        if r['id'] == 58 and r['language'] == 'ja': scenes.setdefault(r['ref'], []).append(r)
    for ref, tr in story_translations().items():
        if ref not in scenes: raise SystemExit(f'scene {ref}: no JP resource')
        for r in scenes[ref]:
            arc = int(r['archive']); pi, ei = r['pack'], r['entry']
            _, data = read_original(pi, ei, arc)
            ids = {mid for mid, _ in parse_mcd(data)['msgs']}
            if ids != set(tr):
                raise SystemExit(f'scene {ref} {r["key"]}: ids differ; missing {sorted(ids-set(tr))[:8]} extra {sorted(set(tr)-ids)[:8]}')
            new, _ = rebuild_local_font(data, tr, FONT, OUT/f'preview_{ref}.png', compact=True)
            decoded[(arc, pi, ei)] = new; applied[r['key']] = len(tr)
            ci = companion(pi, ei, arc)
            if ci is not None:
                _, ext = read_original(pi, ci, arc)
                decoded[(arc, pi, ci)] = sync_companion(new, ext)
    # 4. compress and assemble packs (entry order preserved)
    bypack = {}
    for (arc, pi, ei), data in sorted(decoded.items()):
        assert mcd_length_ok(data), f'MCD length field wrong in {arc}:{pi}:{ei}'
        if data[:4] == b'pDCM':
            s6 = struct.unpack_from('<I', data, 0x30)[0]
            assert s6 % 0x1000 == 0, f'embedded AIF not 4096-aligned in {arc}:{pi}:{ei} ({s6:#x})'
        cache = OUT/(f'p{pi}_e{ei}.slz' if arc == 0 else f'a1_p{pi}_e{ei}.slz')
        blob = cache.read_bytes() if cache.exists() else None
        if blob is None or decode_native_slz(blob)[0] != data:
            orig, _ = read_original(pi, ei, arc)
            print(f'compress {arc}:{pi}:{ei} ({len(data):,} bytes)', flush=True)
            blob = compress(orig, data); cache.write_bytes(blob)
        bypack.setdefault((arc, pi), {})[ei] = (blob, len(data))
    packs = []; skipped_packs = []
    for (arc, pi), rep in sorted(bypack.items()):
        p = PACKSA[arc][pi]
        with ARCS[arc].open('rb') as f:
            f.seek(p['off']); orig = f.read(p['tot'])
        new = build_pack(orig, rep)
        slot = (p['tot'] + 0x7ff) & ~0x7ff
        if len(new) > slot and not can_grow(arc, p['off'], slot):   # packs inside blocks must fit their original slot
            print(f'  pack {arc}:{pi} {len(new)} > slot {slot}: optimal recompression', flush=True)
            for ei, (blob, n) in list(rep.items()):
                orig_e, data = read_original(pi, ei, arc)
                dec = decoded[(arc, pi, ei)]
                if orig_e[3] == 3:
                    b2 = slz_compress_v3(dec, template=orig_e[:32], optimal=True)
                    assert decode_native_slz(b2)[0] == dec
                    if len(b2) < len(blob): rep[ei] = (b2, n)
            new = build_pack(orig, rep)
            if len(new) > slot and not can_grow(arc, p['off'], slot):   # no aliasing (breaks entry order): leave this pack untranslated
                print(f'  pack {arc}:{pi} still too big -> kept original (untranslated)', flush=True)
                skipped_packs.append(f'{arc}:{pi}')
                continue
            print(f'  -> {len(new)}', flush=True)
        name = f'pack{pi}.bin' if arc == 0 else f'a1_pack{pi}.bin'; (OUT/name).write_bytes(new)
        packs.append({'arc': arc, 'pack': pi, 'offset': p['off'], 'file': name, 'sha256': sha(new), 'entries': sorted(rep)})
    manifest = {'format': 'reloc-2', 'packs': packs, 'translations': applied,
                'messages': sum(applied.values()), 'skipped_packs': skipped_packs, 'global_glyphs': len(chars), 'glyph_mapping': mapping}
    (OUT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"BUILD OK: {len(packs)} packs, {manifest['messages']} messages; archives untouched")

def all_records(toc):
    """Every (nsect, bytes, start) record: pack table at +0x6c and block table (~+0x21e00)."""
    out = []
    for o in range(0x6c, len(toc) - 12, 12):
        n, b, st = struct.unpack_from('<3I', toc, o)
        if n and n * 0x800 == b: out.append((o, n, b, st))
    return out

def apply():
    if game_running(): raise SystemExit('Close the game first.')
    man = json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    restore()
    new = {}
    for p in man['packs']:
        new[(p.get('arc', 0), p['offset'])] = (p['pack'], p)
    with ARCS[0].open('rb') as tf:
        toc = read_toc(tf)
    used = set()
    for arc in (0, 1):
        byoff = {off: v for (a, off), v in new.items() if a == arc}
        if not byoff: continue
        recs = [r for r in all_records(toc) if (r[3] >> 28) == arc]
        with ARCS[arc].open('r+b') as f:
            for o, n, b, st in recs:
                lo = (st & 0x0fffffff) * 0x800; hi = lo + b
                inside = [off for off in byoff if lo <= off < hi]
                if not inside: continue
                blob = bytearray(); pos = lo
                while pos < hi:
                    f.seek(pos); hd = f.read(16); assert hd[:4] == b'KCAP', (arc, hex(o), pos)
                    tot = struct.unpack_from('<I', hd, 12)[0]
                    nxt = (pos + tot + 0x7ff) & ~0x7ff
                    if pos in byoff:
                        meta = byoff[pos][1]; part = (OUT/meta['file']).read_bytes()
                        assert sha(part) == meta['sha256'], meta['file']
                        # later packs must keep their ORIGINAL offsets; only the last may grow
                        if len(part) > nxt - pos and nxt < hi:
                            raise SystemExit(f'pack {arc}:{byoff[pos][0]} outgrew its slot in record {o:#x}: {len(part)} > {nxt-pos}')
                    else:
                        f.seek(pos); part = f.read(tot)
                    blob += part + bytes(max(0, nxt - pos - len(part)))
                    pos = nxt
                assert pos >= hi
                f.seek(0, 2); end = f.tell(); start = (end + 0x7ff) & ~0x7ff
                f.write(bytes(start - end)); f.write(blob); f.write(bytes((-len(blob)) % 0x800))
                size = (len(blob) + 0x7ff) & ~0x7ff
                assert start // 0x800 < (1 << 28)
                struct.pack_into('<3I', toc, o, size // 0x800, size, (arc << 28) | (start // 0x800))
                used.update((arc, x) for x in inside)
            f.flush(); os.fsync(f.fileno())
    missing = [(a, v[0]) for (a, off), v in new.items() if (a, off) not in used]
    if missing: print('WARNING: packs not referenced by any TOC record:', missing)
    with ARCS[0].open('r+b') as tf:
        write_toc(tf, toc); tf.flush(); os.fsync(tf.fileno())
    print(f"APPLIED {len(used)} packs")

if __name__ == '__main__':
    {'build': build, 'apply': apply, 'restore': restore}[sys.argv[1]]()
