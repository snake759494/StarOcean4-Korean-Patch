"""Merge issue #2 retranslations (localization/check/issue2_ko_*.json) into the UI batches and
refresh the Japanese source text of those units with the fixed codec (ruby / arena codes)."""
import json,glob,re,sys
sys.path.insert(0,'.'); sys.path.insert(0,'tools')
from pathlib import Path
from localization.codec import decode, LATIN
import audit_ruby as A   # reuses its readable() helpers (GMAP + local font OCR)
UI=Path('localization/ui')
ko={}
for f in sorted(glob.glob('localization/check/issue2_ko_*.json')): ko.update(json.load(open(f,encoding='utf-8')))
work=json.load(open('localization/check/issue2_work.json',encoding='utf-8'))
assert set(ko)==set(work), (set(work)-set(ko), set(ko)-set(work))
def ja_text(k):
    key,mid=work[k]['refs'][0]
    t=decode(A.raw_of(key,mid),local=True)
    def sub(m):
        n=int(m.group(1))
        if n<=1888: return A.GMAP.get(n,'□')
        if n<=2099: return LATIN.get(n,'□')
        return A.lmap(key).get(n-3072,'■')
    return re.sub(r'\{G:(\d+)\}',sub,t)
for f in glob.glob(str(UI/'batch_*_ko.json')):
    kf=json.load(open(f,encoding='utf-8')); bf=f.replace('_ko.json','.json'); b=json.load(open(bf,encoding='utf-8'))
    n=0
    for k in list(kf):
        if k in ko:
            kf[k]=ko[k]; b[k]['ja']=ja_text(k); n+=1
    if n:
        json.dump(kf,open(f,'w',encoding='utf-8'),ensure_ascii=False,indent=0)
        json.dump(b,open(bf,'w',encoding='utf-8'),ensure_ascii=False,indent=0)
        print(Path(f).name,n)
for name in ('units','units2'):
    p=UI/f'{name}.json'; us=json.load(open(p,encoding='utf-8')); n=0
    for u in us:
        if str(u['u']) in ko: u['ja']=ja_text(str(u['u'])); n+=1
    if n: json.dump(us,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=0); print(name,n)
