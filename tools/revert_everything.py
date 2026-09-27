import json,os,hashlib
BAK=r"C:\Users\Jay\so4_kr_patch_backup"
items=[]
for name in ('patch_manifest_all.json','patch_manifest_0000.json'):
    p=os.path.join(BAK,name)
    if os.path.exists(p):
        v=json.load(open(p)); items+= v if isinstance(v,list) else [v]
p=os.path.join(BAK,'patch_manifest.json')
if os.path.exists(p):
    m=json.load(open(p))
    if not any(x['offset']==m['offset'] and x['game_bin']==m['game_bin'] for x in items): items.append(m)
seen=set(); n=0; bad=0
for it in items:
    key=(it['game_bin'],it['offset'])
    if key in seen: continue
    seen.add(key)
    if not os.path.exists(it['backup']): print("MISSING backup",it['backup']); bad+=1; continue
    orig=open(it['backup'],'rb').read()
    if hashlib.md5(orig).hexdigest()!=it['orig_md5']:
        print("MD5 MISMATCH, skipped",hex(it['offset'])); bad+=1; continue
    with open(it['game_bin'],'r+b') as f:
        f.seek(it['offset']); f.write(orig)
    n+=1
print(f"restored {n} region(s), {bad} problem(s)")
for f_ in sorted({i['game_bin'] for i in items}): print("  touched:",os.path.basename(f_))
