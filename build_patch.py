"""Build a reversible Japanese-slot Hangul font and menu demonstration patch."""
from pathlib import Path
import sys, json, struct, hashlib, io, time, subprocess, tempfile
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'tools'))
from slz import slz_decompress
from slzenc import slz_compress_v3,slz_compress
from verify_slz import decode_native_v3
from mcdlib import parse_mcd
from render import aif_alpha, dds_bc7
from bc7enc import encode_bc7_alpha, encode_bc7_white_alpha4
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from localization.codec import encode, literal_chars, ENCODING
from localization.tutorial_ko import K as TUTORIAL
from localization.system_ko import K as SYSTEM
from localization.menus_ko import K as MENUS
from localization.menus_more_ko import K as MORE_MENUS
from localization.battle_records_ko import K as BATTLE_RECORDS
from localization.skills_ko import K as SKILLS
from localization.skill_descriptions_ko import K as SKILL_DESCRIPTIONS
from localization.world_names_ko import K as WORLD_NAMES
from localization.items_ko import K as ITEMS
from localization.item_descriptions_ko import K as ITEM_DESCRIPTIONS
from localization.factors_ko import K as FACTORS
from localization.monsters_ko import K as MONSTERS
from localization.duplicates import expand
from localization.local_font import rebuild as rebuild_local_font
from localization.opening_ko import K as OPENING
from localization.story_65743_ko import K as STORY_65743

GAME = Path(r'C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster')
OUT = ROOT/'build'
TRANSLATIONS = {
    '15:1': {
        0x4e95:'게임 난이도를 선택합니다. 시작 후에는 변경할 수 없습니다.',
        0x4e97:'쉬운 난이도입니다.\n실시간 전투가 익숙하지 않은 분께 추천합니다.',
        0x4e98:'보통 난이도입니다.\n일반적인 난이도로 플레이하려면 선택하세요.',
        0x4e99:'숙련자를 위한 어려운 난이도입니다.\n특정 조건을 달성하면 선택할 수 있습니다.',
        0x4e9a:'가장 어려운 난이도입니다.\n최고의 도전을 원하는 분께 추천합니다.',
    },
    '15:2': {
        **{i:'확인' for i in [0x27100,0x27102,0x27104,0x27106,0x27108,0x2710a,0x2710c,0x2710e,0x27110,0x274fb]},
        **{i:'취소' for i in [0x27105,0x27107,0x27109,0x2710b,0x274e8,0x274ea,0x274ec,0x274ee,0x274ef,0x274f1,0x274f3,0x274f5,0x274f7,0x274f9,0x278d7]},
    },
    '5:0': {0x3d:'예',0x3e:'아니요',0x3f:'취소',0x40:'확인',0x41:'확인',0x42:'취소'},
    '534:59': {
        0x99:'배틀 시뮬레이터에 오신 것을\n환영합니다.',
        0x9a:'전투 조작 방법을 설명합니다.\n원하는 교육 과정을 선택하세요.',
        0x9b:'원하는 수업을 선택하세요.',
        0x9c:'교육 과정 메뉴로 돌아가기',
        0x9d:'배틀 시뮬레이터 종료',
        0x9e:'배틀 시뮬레이터',
        0x9f:'주의',0xa0:'안내',0xb8:'메뉴',0xb9:'교육 과정 메뉴',0xba:'설명',0xbb:'목록',
    },
    '541:0': {
        0x30d40:'다음 수업',0x30d41:'교육 과정 변경',0x30d42:'수업 다시 시작',
        0x30d43:'배틀 시뮬레이터 종료',0x30d44:'돌아가기',0x30d45:'현재 수업 다시 시작',
        0x30d46:'기본 교육',0x30d47:'사이드 아웃 교육',0x30d48:'링크 콤보 교육',
        0x30d49:'기타 설명',0x30d4a:'전투 연습',
        0x30d4b:'이동',0x30d4c:'공격',0x30d4d:'공격 대상 변경',0x30d4e:'점프',
        0x30d4f:'가드',0x30d50:'러시 모드',0x30d51:'리더 변경',0x30d52:'카메라 조작',
        0x30d53:'실전 연습',0x30d54:'사이드 아웃의 기본',0x30d55:'사이드 아웃 활용',
        0x30d56:'분노 표시',0x30d57:'실전 연습',0x30d58:'링크 콤보',0x30d59:'러시 콤보',
        0x30d5a:'전투 시작 조건',0x30d5b:'보너스 보드',0x30d5c:'능력 강화',
        0x30d5d:'비트 시스템',0x30d5e:'전투 연습',
    },
}
TRANSLATIONS['5:0'].update({0x9c65:'시뮬레이터',0xabe0:'배틀 시뮬레이터'})
TRANSLATIONS['541:0'].update(TUTORIAL)
TRANSLATIONS['5:0'].update(SYSTEM)
TRANSLATIONS['5:0'].update(BATTLE_RECORDS)
TRANSLATIONS['5:0'].update(SKILLS)
TRANSLATIONS['5:0'].update(SKILL_DESCRIPTIONS)
TRANSLATIONS['5:0'].update(WORLD_NAMES)
TRANSLATIONS['5:0'].update(ITEMS)
TRANSLATIONS['5:0'].update(ITEM_DESCRIPTIONS)
TRANSLATIONS['5:0'].update(FACTORS)
TRANSLATIONS['5:0'].update(MONSTERS)
TRANSLATIONS['15:1'].update(MENUS)
TRANSLATIONS['15:1'].update(MORE_MENUS)
AUTHORED_TRANSLATIONS={key:dict(values) for key,values in TRANSLATIONS.items()}
TRANSLATIONS=expand(TRANSLATIONS)

class ResourceCapacityError(ValueError): pass

def sha(b): return hashlib.sha256(b).hexdigest()
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def put(b,o,n): struct.pack_into('<I',b,o,n)

def encode_index(n):
    assert 0 < n < 0x4000
    return bytes([n]) if n < 128 else bytes([0x80|(n&127),n>>7])

def read_resource(pi,ei):
    p=PACKS[pi]; e=p['e'][ei]
    offset=p['off']+e[4]
    span=min([r[4] for r in p['e'] if r[4]>e[4]]+[p['tot']])-e[4]
    with (GAME/'0000.bin').open('rb') as f: f.seek(offset); raw=f.read(span)
    assert raw[:3]==b'SLZ', (pi,ei,raw[:4])
    decoded,_=decode_native_v3(raw) if raw[3]==3 else slz_decompress(raw)
    assert len(decoded)==e[3]
    return offset,raw,decoded

def extend_font(data, chars):
    assert len(chars)<=973, 'Global Hangul glyphs would overlap the local font bank'
    d=bytearray(data); m=parse_mcd(d); o=m['sect']
    counts=[u32(d,o[0]+16*i) for i in range(m['cnt'][0])]
    assert counts==[1888,211]
    total=sum(counts)
    end=o[4]+(total+len(chars))*24
    texpos=(end+15)&~15
    growth=0
    if texpos+16>o[6]:
        growth=((texpos+16-o[6]+4095)//4096)*4096
        d[o[6]:o[6]]=bytes(growth)
        for field in (4,12,20): put(d,field,u32(d,field)+growth)
        put(d,0x18+6*4,o[6]+growth)
        m=parse_mcd(d); o=m['sect']
    atlas,W,H,images,pixels=aif_alpha(d,o[6])
    maxbottom=max(struct.unpack_from('<f',d,o[4]+i*24+20)[0] for i in range(total))
    pitch=64; columns=W//pitch
    ybase=((round(maxbottom*H)+7)//8)*8
    rows=(len(chars)+columns-1)//columns
    assert ybase+rows*pitch<=H
    original=atlas.copy()
    font=ImageFont.truetype(str(GAME/'NanumSquareNeo-cBd.ttf'),64)
    mapping={}
    for j,ch in enumerate(chars):
        x=(j%columns)*pitch; y=ybase+(j//columns)*pitch
        tile=Image.new('L',(pitch,pitch)); draw=ImageDraw.Draw(tile)
        box=draw.textbbox((0,0),ch,font=font)
        draw.text(((pitch-box[2]+box[0])//2-box[0],(pitch-box[3]+box[1])//2-box[1]),ch,font=font,fill=255)
        assert original.crop((x,y,x+pitch,y+pitch)).getbbox() is None
        atlas.paste(tile,(x,y))
        struct.pack_into('<II4f',d,o[4]+(total+j)*24,72,0,x/W,y/H,(x+pitch)/W,(y+pitch)/H)
        mapping[ch]=total+j+1
    put(d,o[0]+16,counts[1]+len(chars))
    put(d,0x18+5*4,texpos)
    struct.pack_into('<4I',d,texpos,W,H,0,0)
    # Keep every original compressed texture block outside the added blank rows.
    pos=pixels
    for iw,ih,ds in images:
        assert ds==iw*ih
        src=atlas if (iw,ih)==(W,H) else atlas.resize((iw,ih),Image.Resampling.LANCZOS)
        y0=(ybase*ih//H)//4*4
        y1=((ybase+rows*pitch)*ih//H+3)//4*4
        blob=encode_bc7_white_alpha4(np.asarray(src.crop((0,y0,iw,y1)),dtype=np.uint8))
        start=pos+(y0//4)*(iw//4)*16
        d[start:start+len(blob)]=blob
        pos+=ds
    assert len(d)==len(data)+growth
    atlas.crop((0,ybase,W,ybase+rows*pitch)).save(OUT/'hangul_atlas.png')
    # Remove unused transparent rows, preserving all occupied pixel blocks.
    # This creates space in the archive without replacing any original glyph.
    # Both BC7 mip levels need four-pixel block alignment; eight rows suffice.
    newH=max(6144,((ybase+rows*pitch+7)//8)*8)
    assert ybase+rows*pitch<=newH
    assert atlas.crop((0,newH,W,H)).getbbox() is None
    head=bytearray(d[:pixels]); texture=bytearray(); oldpos=pixels
    imgpos=o[6]+0x10; image_headers=[]
    while imgpos<pixels:
        tag=bytes(d[imgpos:imgpos+4]); size=u32(d,imgpos+4)
        if tag==b'Xgmi': image_headers.append(imgpos)
        if tag==b' FMA': break
        imgpos+=size
    amf=imgpos
    assert len(image_headers)==len(images)==2
    sizes=[]
    for (iw,ih,ds),desc in zip(images,image_headers):
        nh=ih*newH//H; nsize=iw*nh
        texture+=d[oldpos:oldpos+nsize]; oldpos+=ds; sizes.append(nsize)
        struct.pack_into('<H',head,desc+0x2a,nh)
        put(head,desc+0x38,nh); put(head,desc+0x3c,nsize)
    for i in range(total+len(chars)):
        for field in (12,20):
            at=o[4]+i*24+field
            v=struct.unpack_from('<f',head,at)[0]
            struct.pack_into('<f',head,at,v*H/newH)
    put(head,texpos+4,newH)
    put(head,amf+4,0x1d0+sum(sizes))
    put(head,amf+0x60,sum(sizes))
    put(head,amf+0xb0,sizes[0])
    put(head,amf+0x110,sizes[1]); put(head,amf+0x118,sizes[0])
    d=head+texture
    # Unlike an ordinary nested chunk, the MCD length includes its first 16
    # bytes. Every original pDCM resource uses the complete decoded length.
    put(d,0x14,len(d))
    return bytes(d),mapping

def encode_text(s,mapping):
    return encode(s,mapping)

def replace_messages(data, translations, mapping):
    d=bytearray(data); m=parse_mcd(d); base=m['sect'][3]; end=m['sect'][4] or len(data)
    assert base and end>base
    pool=bytearray(); found=set(); shared={}
    offsets=sorted({off for _,off in m['msgs']}|{end-base})
    bounds=dict(zip(offsets,offsets[1:]))
    for i,(mid,off) in enumerate(m['msgs']):
        nxt=bounds.get(off,end-base)
        raw=data[base+off:base+nxt]
        if mid in translations:
            raw=encode_text(translations[mid],mapping); found.add(mid)
        elif nxt==end-base:
            raw=raw.rstrip(b'\0')+b'\0'
        if raw not in shared:
            shared[raw]=len(pool); pool+=raw
        put(d,m['sect'][2]+i*8+4,shared[raw])
    assert found==set(translations)
    if len(pool)>end-base:
        align=0xfff if m['sect'][6] else 15   # keep an embedded AIF 4096-aligned
        growth=(len(pool)-(end-base)+align)&~align
        d[end:end]=bytes(growth)
        for index in (4,5,6):
            if m['sect'][index]:put(d,0x18+index*4,m['sect'][index]+growth)
        for field in (4,12,20):
            if u32(d,field):put(d,field,u32(d,field)+growth)
        end+=growth
    d[base:end]=pool+bytes(end-base-len(pool))
    return bytes(d)

def save_resource(pi,ei,offset,orig,modified):
    started=time.monotonic()
    print(f'Compressing pack {pi}, entry {ei}: {len(modified):,} bytes',flush=True)
    cached=OUT/f'p{pi}_e{ei}.slz'
    compressed=cached.read_bytes() if cached.exists() else None
    if compressed is None or compressed[3]!=orig[3] or decode_native_v3(compressed)[0]!=modified:
        if orig[3]==1:
            compressed=slz_compress(modified)
            h=bytearray(orig[:32]); h[3]=1; put(h,8,len(compressed)-32); put(h,12,len(modified))
            compressed=bytes(h)+compressed[32:]
        else: compressed=slz_compress_v3(modified,template=orig)
    # Original chunks are already valid streams. Reuse them where their decoded
    # content is unchanged and they are smaller than the newly encoded chunk.
    original_decoded,_=decode_native_v3(orig) if orig[3]==3 else slz_decompress(orig)
    def chunks(buf):
        pos=u32(buf,20); out=[]; usize=u32(buf,12); size=buf[25]<<10
        for start in range(0,usize,size):
            n=struct.unpack_from('<H',buf,pos)[0]
            actual=n or min(size,usize-start)
            out.append(buf[pos:pos+actual+2]); pos+=actual+2
        return out
    oldchunks=chunks(orig); reused=0
    size=orig[25]<<10
    original_chunks={}
    if orig[3]==3:
        for i,chunk in enumerate(oldchunks):
            content=original_decoded[i*size:(i+1)*size]
            if content not in original_chunks or len(chunk)<len(original_chunks[content]):original_chunks[content]=chunk
    def reuse_original(encoded):
        body=bytearray();count=0
        for i,new in enumerate(chunks(encoded)):
            old=original_chunks.get(modified[i*size:(i+1)*size])
            if old is not None and len(old)<len(new):body+=old;count+=1
            else:body+=new
        header=bytearray(encoded[:32]);put(header,8,len(body))
        return bytes(header)+body,count
    compressed,reused=reuse_original(compressed)
    if len(compressed)>len(orig) and compressed[3]==3:
        print('  using minimum-token compression to fit entry',flush=True)
        helper=ROOT/'tools/SlzOptimal.exe'
        if helper.exists():
            with tempfile.TemporaryDirectory(prefix='so4-slz-') as folder:
                temp=Path(folder);(temp/'source').write_bytes(modified);(temp/'template').write_bytes(orig[:32])
                subprocess.run([str(helper),str(temp/'source'),str(temp/'template'),str(temp/'output')],check=True,creationflags=0x08000000,capture_output=True)
                compressed=(temp/'output').read_bytes()
        else: compressed=slz_compress_v3(modified,template=orig,optimal=True)
        compressed,reused=reuse_original(compressed)
    cached.write_bytes(compressed)
    print(f'  retained {reused} smaller original chunks',flush=True)
    if len(compressed)>len(orig): raise ResourceCapacityError(f'Compressed resource exceeds span: {len(compressed)} > {len(orig)}')
    actual,chunks=decode_native_v3(compressed)
    assert actual==modified
    patched=compressed+orig[len(compressed):]
    label=f'p{pi}_e{ei}'
    (OUT/f'{label}.original.bin').write_bytes(orig)
    (OUT/f'{label}.patched.bin').write_bytes(patched)
    print(f'  verified {len(chunks)} chunks; {len(compressed):,}/{len(orig):,} bytes; {time.monotonic()-started:.1f}s',flush=True)
    return {'pack':pi,'entry':ei,'offset':offset,'span':len(orig),'original':f'{label}.original.bin','patched':f'{label}.patched.bin','original_sha256':sha(orig),'patched_sha256':sha(patched),'decoded_sha256':sha(modified),'compressed_size':len(compressed),'verified_chunks':len(chunks)}

def save_decoded_size(pi,ei,before,after):
    offset=PACKS[pi]['off']+16+ei*16+8
    with (GAME/'0000.bin').open('rb') as f:f.seek(offset);original=f.read(4)
    assert struct.unpack('<I',original)[0]==before
    patched=struct.pack('<I',after);label=f'p{pi}_e{ei}_size'
    (OUT/f'{label}.original.bin').write_bytes(original)
    (OUT/f'{label}.patched.bin').write_bytes(patched)
    return {'pack':pi,'entry':f'{ei} decoded size','offset':offset,'span':4,'original':f'{label}.original.bin','patched':f'{label}.patched.bin','original_sha256':sha(original),'patched_sha256':sha(patched)}

def preview(fontdata,mapping):
    m=parse_mcd(fontdata); _,W,H,imgs,pos=aif_alpha(fontdata,m['imgoff'])
    atlas=Image.open(io.BytesIO(dds_bc7(fontdata[pos:pos+imgs[0][2]],W,H))).convert('RGBA')
    lines=TRANSLATIONS['15:1'][0x4e98].splitlines()+['확인  취소']
    result=Image.new('RGB',(1150,210),(13,23,37))
    for lineidx,line in enumerate(lines):
        x=24
        for ch in line:
            if ch==' ': x+=18; continue
            idx=1912 if ch=='.' else mapping[ch]
            adv,_,u0,v0,u1,v1=struct.unpack_from('<II4f',fontdata,m['sect'][4]+(idx-1)*24)
            tile=atlas.crop((round(u0*W),round(v0*H),round(u1*W),round(v1*H)))
            tile=tile.resize((max(1,tile.width//2),max(1,tile.height//2)),Image.Resampling.LANCZOS)
            result.paste(tile,(x,24+lineidx*58),tile.getchannel('A'))
            x+=adv//2
    result.save(OUT/'font_render_preview.png')

if __name__=='__main__':
    if '--experimental-full' not in sys.argv:
        from build_opening_repair import main as build_focused_repair
        build_focused_repair()
        raise SystemExit(0)
    OUT.mkdir(exist_ok=True)
    PACKS=json.loads((ROOT/'tools/packs0.json').read_text())
    chars=sorted({c for tr in TRANSLATIONS.values() for s in tr.values() for c in literal_chars(s) if c not in ENCODING and c!='\n'})
    print(f'Adding {len(chars)} Hangul syllables without replacing original glyphs.',flush=True)
    off,orig,data=read_resource(0,65)
    modified,mapping=extend_font(data,chars)
    preview(modified,mapping)
    items=[save_resource(0,65,off,orig,modified)]
    # KCAP directory stores decoded resource size independently of the SLZ header.
    size_offset=PACKS[0]['off']+16+65*16+8
    with (GAME/'0000.bin').open('rb') as f: f.seek(size_offset); original_size=f.read(4)
    assert struct.unpack('<I',original_size)[0]==len(data)
    new_size=struct.pack('<I',len(modified))
    (OUT/'font_size.original.bin').write_bytes(original_size)
    (OUT/'font_size.patched.bin').write_bytes(new_size)
    items.append({'pack':0,'entry':'65 decoded size','offset':size_offset,'span':4,'original':'font_size.original.bin','patched':'font_size.patched.bin','original_sha256':sha(original_size),'patched_sha256':sha(new_size)})
    applied_translations={}; deferred=[]; local_mappings={}
    for key,tr in TRANSLATIONS.items():
        pi,ei=map(int,key.split(':')); off,orig,data=read_resource(pi,ei)
        try:
            modified=replace_messages(data,tr,mapping)
            item=save_resource(pi,ei,off,orig,modified)
        except ResourceCapacityError as ex:
            authored=AUTHORED_TRANSLATIONS.get(key,{})
            deferred.append({'resource':key,'message_ids':sorted(set(tr)-set(authored)),'reason':str(ex)})
            if authored==tr: raise
            print(f'  duplicate propagation deferred: {ex}',flush=True)
            if not authored: continue
            tr=authored
            modified=replace_messages(data,tr,mapping)
            item=save_resource(pi,ei,off,orig,modified)
        items.append(item); applied_translations[key]=tr
        if len(modified)!=len(data):items.append(save_decoded_size(pi,ei,len(data),len(modified)))
    local_translations={'1438:5':OPENING,'1316:6':STORY_65743}
    inventory=json.loads((ROOT/'localization/inventory.json').read_text(encoding='utf-8'))
    fingerprints={r['sha256']:local_translations[f"{r['pack']}:{r['entry']}"] for r in inventory if r.get('archive')=='0000' and f"{r['pack']}:{r['entry']}" in local_translations}
    for r in inventory:
        if r.get('archive')=='0000' and r.get('language')=='ja' and r.get('sha256') in fingerprints:
            local_translations[f"{r['pack']}:{r['entry']}"]=fingerprints[r['sha256']]
    for key,tr in local_translations.items():
        pi,ei=map(int,key.split(':')); off,orig,data=read_resource(pi,ei)
        preview_name='opening_preview.png' if key=='1438:5' else f'story_{pi}_{ei}_preview.png'
        modified,local_mapping=rebuild_local_font(data,tr,GAME/'NanumSquareNeo-cBd.ttf',OUT/preview_name)
        try:item=save_resource(pi,ei,off,orig,modified)
        except ResourceCapacityError:
            modified,local_mapping=rebuild_local_font(data,tr,GAME/'NanumSquareNeo-cBd.ttf',OUT/preview_name,compact=True)
            item=save_resource(pi,ei,off,orig,modified)
        items.append(item)
        if len(modified)!=len(data):items.append(save_decoded_size(pi,ei,len(data),len(modified)))
        applied_translations[key]=tr; local_mappings[key]=local_mapping
    manifest={'format':1,'game_archive':'0000.bin','game_directory':str(GAME),'scope':'Partial localization: opening, tutorial, common menus, battle conditions, skills, item and monster names, equipment effects, selected descriptions and story scenes; full localization incomplete','font':'NanumSquare Neo Bold','runtime_verified':False,'added_glyphs':len(chars),'translations':applied_translations,'deferred_duplicates':deferred,'glyph_mapping':mapping,'local_glyph_mappings':local_mappings,'resources':items}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('BUILD COMPLETE. Archive not modified.',flush=True)
