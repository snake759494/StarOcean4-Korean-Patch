from pathlib import Path
import sys,json,struct,hashlib,io
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from verify_slz import decode_native_v3
from slz import slz_decompress
from render import aif_alpha,dds_bc7
from PIL import Image
import numpy as np
from mcdlib import parse_mcd
from build_patch import encode_text

import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--build-dir',type=Path,default=ROOT/'build')
b=parser.parse_args().build_dir.resolve(); manifest=json.loads((b/'manifest.json').read_text(encoding='utf-8'))
decoded={}; chunks=0
packs=json.loads((ROOT/'tools/packs0.json').read_text())
for key in manifest.get('local_glyph_mappings',{}):
    pi,ei=map(int,key.split(':'))
    entry=packs[pi]['e'][ei]
    companions=[i for i,e in enumerate(packs[pi]['e']) if e[0]==59 and e[1:3]==entry[1:3]]
    for companion in companions:
        assert any(r['pack']==pi and r['entry']==companion for r in manifest['resources']), f'{key}: companion font entry {companion} was not patched'
for item in manifest['resources']:
    for which in ['original','patched']:
        raw=(b/item[which]).read_bytes()
        assert len(raw)==item['span']
        assert hashlib.sha256(raw).hexdigest()==item[which+'_sha256']
        if item['span']==4: continue
        data,cs=decode_native_v3(raw)
        if data[:4] == b'pDCM':
            declared = struct.unpack_from('<I', data, 0x14)[0]
            assert declared == len(data), (item['pack'], item['entry'], which,
                                          'MCD total length mismatch', declared, len(data))
        decoded[(item['pack'],item['entry'],which)]=data
        if which=='patched':
            assert hashlib.sha256(data).hexdigest()==item['decoded_sha256']
            chunks+=len(cs)

old=decoded[(0,65,'original')]; new=decoded[(0,65,'patched')]
if (1438,6,'patched') in decoded:
    opening=decoded[(1438,5,'patched')]
    companion=decoded[(1438,6,'patched')]
    opening_base=struct.unpack_from('<I',opening,48)[0]
    _,w,h,imgs,pos=aif_alpha(opening,opening_base)
    _,cw,ch,cimgs,cpos=aif_alpha(companion,0)
    assert (w,h,imgs)==(cw,ch,cimgs), 'Opening companion texture layout mismatch'
    size=sum(s for _,_,s in imgs)
    assert opening[pos:pos+size]==companion[cpos:cpos+size], 'Opening companion pixels mismatch'
    assert companion[:cpos]==decoded[(1438,6,'original')][:cpos], 'Companion identifiers changed'
om=parse_mcd(old); nm=parse_mcd(new)
oi,ow,oh,_,_=aif_alpha(old,om['imgoff']); ni,nw,nh,_,_=aif_alpha(new,nm['imgoff'])
def rgba(data,model):
    _,w,h,imgs,pos=aif_alpha(data,model['imgoff'])
    return Image.open(io.BytesIO(dds_bc7(data[pos:pos+imgs[0][2]],w,h))).convert('RGBA')
oldrgba=rgba(old,om); newrgba=rgba(new,nm)
for i in range(2099):
    a=struct.unpack_from('<II4f',old,om['sect'][4]+i*24)
    c=struct.unpack_from('<II4f',new,nm['sect'][4]+i*24)
    assert a[:2]==c[:2]
    ob=tuple(round(v*s) for v,s in zip(a[2:],(ow,oh,ow,oh)))
    nb=tuple(round(v*s) for v,s in zip(c[2:],(nw,nh,nw,nh)))
    assert ob==nb,(i,ob,nb)
    assert oi.crop(ob).tobytes()==ni.crop(nb).tobytes(),i
    assert oldrgba.crop(ob).tobytes()==newrgba.crop(nb).tobytes(),i
mapping=manifest['glyph_mapping']
for ch,index in mapping.items():
    a=struct.unpack_from('<II4f',new,nm['sect'][4]+(index-1)*24)
    box=tuple(round(v*s) for v,s in zip(a[2:],(nw,nh,nw,nh)))
    assert ni.crop(box).getbbox(),ch
    pixels=np.asarray(newrgba.crop(box)); visible=pixels[pixels[:,:,3]>240]
    assert len(visible)>0 and np.all(visible[:,:3]>=254),(ch,'incorrect glyph RGB')
translated=0
for key,tr in manifest['translations'].items():
    pi,ei=map(int,key.split(':')); d=decoded[(pi,ei,'patched')]; m=parse_mcd(d)
    resource_mapping=manifest.get('local_glyph_mappings',{}).get(key,mapping)
    if key in manifest.get('local_glyph_mappings',{}):
        local_rgba=rgba(d,m)
        assert len(resource_mapping)==m['hdr'][0]
        for ch,index in resource_mapping.items():
            advance,_,u,v,r,bottom=struct.unpack_from('<II4f',d,m['sect'][4]+(index-1)*24)
            tile=np.asarray(local_rgba.crop((round(u*local_rgba.width),round(v*local_rgba.height),round(r*local_rgba.width),round(bottom*local_rgba.height))))
            visible=tile[tile[:,:,3]>240]
            if ch!=' ': assert len(visible)>0 and np.all(visible[:,:3]>=254),(key,ch)
    original=decoded[(pi,ei,'original')]; before=parse_mcd(original)
    if key not in manifest.get('local_glyph_mappings',{}) and before['sect'][4]:
        assert original[before['sect'][4]:]==d[m['sect'][4]:],(key,'local glyph or texture changed')
    if len(original)!=len(d):
        size_entries=[item for item in manifest['resources'] if item['pack']==pi and item['entry']==f'{ei} decoded size']
        assert len(size_entries)==1,(key,'missing decoded size update')
        assert struct.unpack('<I',(b/size_entries[0]['patched']).read_bytes())[0]==len(d)
    def message_blobs(data,model):
        base=model['textbase']; end=(model['textend'] or len(data))-base
        offsets=sorted({off for _,off in model['msgs']}|{end})
        bounds=dict(zip(offsets,offsets[1:]))
        return {mid:data[base+off:base+bounds.get(off,end)].rstrip(b'\0') for mid,off in model['msgs']}
    oldtexts=message_blobs(original,before); newtexts=message_blobs(d,m)
    assert oldtexts.keys()==newtexts.keys()
    for mid,raw in oldtexts.items():
        if str(mid) not in tr: assert newtexts[mid]==raw,(pi,ei,mid)
    messages=dict(m['msgs'])
    for mid,text in tr.items():
        start=m['textbase']+messages[int(mid)]
        expected=encode_text(text,resource_mapping)
        assert d[start:start+len(expected)]==expected
        translated+=1
report={'status':'PASS','compressed_chunks_checked':chunks,'original_glyphs_pixel_identical':2099,'original_rgba_preserved':True,'hangul_rgb_white':True,'new_hangul_glyphs':len(mapping),'local_fonts_rebuilt':{key:len(value) for key,value in manifest.get('local_glyph_mappings',{}).items()},'translated_messages_checked':translated,'untranslated_messages_preserved':True,'font_dimensions':[nw,nh],'runtime_verified':False}
(b/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
