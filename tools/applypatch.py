import sys,io,json,os,hashlib,shutil
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
GAMEBIN=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster\0001.bin"
BAKDIR=r"C:\Users\Jay\so4_kr_patch_backup"
info=json.load(open('patchinfo.json'))
blob=open('newentry.bin','rb').read()
off,span=info['abs_off'],info['span']
assert len(blob)<=span, "patch larger than span"
os.makedirs(BAKDIR,exist_ok=True)
bakfile=os.path.join(BAKDIR,f"orig_{off:012x}_{span}.bin")
with open(GAMEBIN,'rb') as f:
    f.seek(off); orig=f.read(span)
assert len(orig)==span
if not os.path.exists(bakfile):
    with open(bakfile,'wb') as g: g.write(orig)
    print(f"backup written: {bakfile} ({len(orig)} bytes, md5={hashlib.md5(orig).hexdigest()})")
else:
    print(f"backup already exists: {bakfile}")
meta={'game_bin':GAMEBIN,'offset':off,'span':span,'orig_md5':hashlib.md5(orig).hexdigest(),
      'backup':bakfile,'desc':'pack#668 id=30 type=0x0221 JP global font atlas'}
json.dump(meta,open(os.path.join(BAKDIR,'patch_manifest.json'),'w'),indent=1)
# write
with open(GAMEBIN,'r+b') as f:
    f.seek(off); f.write(blob)
print(f"patched {len(blob)} bytes at 0x{off:x} (span 0x{span:x}, {span-len(blob)} bytes of original tail left in place)")
