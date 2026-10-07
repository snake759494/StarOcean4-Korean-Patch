"""Issue #2 audit: translation units whose Korean text still carries a control code that
swallowed the rest of the message (ruby 9080, arena branches ae/af/b0/b1/b280)."""
import json,glob,re,sys
sys.path.insert(0,'.')
from pathlib import Path
from localization.codec import decode, LATIN
GMAP={int(k):v['c'] for k,v in json.load(open('localization/global_charmap.json',encoding='utf-8')).items()}
LM={}
def lmap(key):
    if key not in LM:
        sys.path.insert(0,'tools'); import transcribe_ui; LM[key]=transcribe_ui.local_map(key)
    return LM[key]
def readable(raw,key):
    t=decode(raw,local=True)
    t=re.sub(r'\{RAW:90809080\}(.*?)\{RAW:00\}(.*?)\{RAW:9180\}',lambda m:'《'+m.group(2)+'|'+m.group(1)+'》',t)
    t=re.sub(r'\{RAW:(a[ef]|b[0-2])80([0-9a-f]{0,2})\}',lambda m:'⟦'+m.group(1)+m.group(2)+'⟧',t)
    t=re.sub(r'\{G:(\d+)\}',lambda m:GMAP.get(int(m.group(1)),LATIN.get(int(m.group(1)),'□')) if int(m.group(1))<=2099 else lmap(key).get(int(m.group(1))-3072,'■'),t)
    return t
units={}
for n in ('units','units2'):
    for u in json.load(open(f'localization/ui/{n}.json',encoding='utf-8')): units[u['u']]=u
src={}
def raw_of(key,mid):
    if key not in src: src[key]={r['id']:r for r in json.load(open(f'localization/source/{key}.json',encoding='utf-8'))}
    return bytes.fromhex(src[key][mid]['raw'])
ko={}; where={}
for f in glob.glob('localization/ui/batch_*_ko.json'):
    for k,v in json.load(open(f,encoding='utf-8')).items(): ko[k]=v; where[k]=Path(f).name
BAD=re.compile(r'\{RAW:((?:90|ae|af|b0|b1|b2)80[0-9a-f]*)\}')
work={}
for k,v in ko.items():
    bad=[m.group(1) for m in BAD.finditer(v)]
    if not bad: continue
    u=units[int(k)]; key,mid=u['refs'][0]
    work[k]={'file':where[k],'refs':u['refs'],'ja':readable(raw_of(key,mid),key),'ko_old':v}
json.dump(work,open('localization/check/issue2_work.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(len(work),'units')
