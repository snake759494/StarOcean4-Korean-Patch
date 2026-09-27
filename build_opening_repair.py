"""Focused repair: retain menu string offsets and synchronize movie font pair."""
import json, shutil, struct
from pathlib import Path
import build_patch as bp
from localization.codec import encode, messages
from localization.local_font import rebuild
from localization.opening_ko import K
from render import aif_alpha
from verify_slz import decode_native_slz

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'build'

def original_resource(pi,ei):
    p=bp.PACKS[pi]; e=p['e'][ei]
    for folder in (OUT,ROOT/'build_opening_repair',ROOT/'build_failed_5381'):
        path=folder/f'p{pi}_e{ei}.original.bin'
        if path.exists():
            raw=path.read_bytes()
            old_manifest=folder/'manifest.json'
            if old_manifest.exists():
                doc=json.loads(old_manifest.read_text(encoding='utf-8'))
                old=next((r for r in doc['resources'] if r['pack']==pi and r['entry']==ei),None)
                if old: assert bp.sha(raw)==old['original_sha256'], 'Original backup damaged'
            decoded=decode_native_slz(raw)[0]
            assert len(decoded)==e[3]
            return p['off']+e[4],raw,decoded
    return bp.read_resource(pi,ei)

def main():
    OUT.mkdir(exist_ok=True)
    base = ROOT / 'build_verified_426'
    manifest = json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    for item in manifest['resources']:
        for field in ('original', 'patched'):
            shutil.copy2(base/item[field], OUT/item[field])
    bp.OUT = OUT
    bp.PACKS = json.loads((ROOT/'tools/packs0.json').read_text())
    # Baseline payloads predate the MCD total-length correction. Rebuild the
    # copied resource too; otherwise the default builder retains that defect.
    old_font = next(r for r in manifest['resources'] if r['pack']==0 and r['entry']==65)
    font_original = (base/old_font['original']).read_bytes()
    font_data = bytearray(decode_native_slz((base/old_font['patched']).read_bytes())[0])
    struct.pack_into('<I', font_data, 0x14, len(font_data))
    corrected_font = bp.save_resource(0,65,old_font['offset'],font_original,bytes(font_data))
    manifest['resources'] = [corrected_font if r is old_font else r for r in manifest['resources']]
    mapping = manifest['glyph_mapping']
    tr = {int(k): v for k,v in manifest['translations']['15:1'].items()}
    tr[20117] = '난이도를 선택합니다. 시작 후에는 변경할 수 없습니다.'
    original = (base/'p15_e1.original.bin').read_bytes()
    d = bytearray(decode_native_slz(original)[0])
    section = struct.unpack_from('<7I', d, 24)
    count = struct.unpack_from('<I',d,60)[0]
    rows = dict(struct.unpack_from('<II',d,section[2]+8*i) for i in range(count))
    slots = messages(d)
    for mid,text in tr.items():
        raw = encode(text,mapping)
        assert len(raw) <= len(slots[mid]), (mid,len(raw),len(slots[mid]))
        pos=section[3]+rows[mid]
        d[pos:pos+len(slots[mid])] = raw + bytes(len(slots[mid])-len(raw))
    assert d[section[2]:section[3]] == decode_native_slz(original)[0][section[2]:section[3]]
    old=next(r for r in manifest['resources'] if r['pack']==15 and r['entry']==1)
    item=bp.save_resource(15,1,old['offset'],original,bytes(d))
    manifest['resources']=[item if r is old else r for r in manifest['resources']]
    manifest['translations']['15:1']=tr

    off, raw, source = original_resource(1438,5)
    patched, localmap = rebuild(source,K,bp.GAME/'NanumSquareNeo-cBd.ttf',OUT/'opening_preview.png',compact=True)
    manifest['resources'].append(bp.save_resource(1438,5,off,raw,patched))
    assert len(source)==len(patched)
    off, raw, external = original_resource(1438,6)
    source_base = struct.unpack_from('<I',source,48)[0]
    patched_base = struct.unpack_from('<I',patched,48)[0]
    _,w,h,imgs,source_pixels = aif_alpha(source,source_base)
    _,pw,ph,pimgs,patched_pixels = aif_alpha(patched,patched_base)
    _,ew,eh,eimgs,external_pixels = aif_alpha(external,0)
    assert (w,h,imgs)==(pw,ph,pimgs)==(ew,eh,eimgs)
    size=sum(s for _,_,s in imgs)
    assert source[source_pixels:source_pixels+size]==external[external_pixels:external_pixels+size]
    paired=bytearray(external)
    paired[external_pixels:external_pixels+size]=patched[patched_pixels:patched_pixels+size]
    assert paired[:external_pixels]==external[:external_pixels]
    manifest['resources'].append(bp.save_resource(1438,6,off,raw,bytes(paired)))
    manifest['translations']['1438:5']=K
    manifest['local_glyph_mappings']={'1438:5':localmap}
    manifest['scope']='Focused opening/font-pair repair and menu offsets; not a full localization'
    manifest['runtime_verified']=False
    manifest['runtime_status']='UNVERIFIED_LENGTH_FIX'
    manifest['repair_notes']=['MCD total length corrected; symptom resolution not established','Original menu message offsets retained','Opening embedded and companion font pixels synchronized; companion headers preserved']
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Focused repair built; game not modified.')

if __name__=='__main__':main()
