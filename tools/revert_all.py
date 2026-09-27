import json,os,hashlib,sys
BAKDIR=r"C:\Users\Jay\so4_kr_patch_backup"
items=[]
p1=os.path.join(BAKDIR,'patch_manifest_all.json')
p0=os.path.join(BAKDIR,'patch_manifest.json')
if os.path.exists(p1): items+=json.load(open(p1))
if os.path.exists(p0):
    m=json.load(open(p0))
    if not any(x['offset']==m['offset'] for x in items): items.append(m)
seen=set(); n=0
for it in items:
    if it['offset'] in seen: continue
    seen.add(it['offset'])
    orig=open(it['backup'],'rb').read()
    if hashlib.md5(orig).hexdigest()!=it['orig_md5']:
        print("MD5 MISMATCH, skipping",hex(it['offset'])); continue
    with open(it['game_bin'],'r+b') as f:
        f.seek(it['offset']); f.write(orig)
    print(f"reverted 0x{it['offset']:x} ({len(orig)} bytes) - {it.get('desc','')}")
    n+=1
print(f"\n{n} region(s) restored to original.")
