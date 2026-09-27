from pathlib import Path
import sys,json,hashlib,collections
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from slz import slz_decompress
from codec import decode,messages
GAME=Path(r'C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster')
out=ROOT/'localization'; (out/'source').mkdir(exist_ok=True)
installed=json.loads((ROOT/'build/manifest.json').read_text(encoding='utf-8'))
originals={r['offset']:ROOT/'build'/r['original'] for r in installed['resources']}
resources=[]
for archive,index in [('0000','packs0.json'),('0001','packs.json')]:
    packs=json.loads((ROOT/'tools'/index).read_text())
    with (GAME/(archive+'.bin')).open('rb') as f:
        for pi,p in enumerate(packs):
            for ei,e in enumerate(p['e']):
                if e[0] not in (9,30,58): continue
                lang=e[1]&0xf0
                if lang not in (0x10,0x20,0x30): continue
                offset=p['off']+e[4]
                if archive=='0000' and offset in originals: raw=originals[offset].read_bytes()
                else: f.seek(offset); raw=f.read(e[3]+64)
                try: d=slz_decompress(raw)[0] if raw[:3]==b'SLZ' else raw[:e[3]]
                except Exception as ex:
                    resources.append({'archive':archive,'pack':pi,'entry':ei,'error':str(ex)}); continue
                if d[:4]!=b'pDCM': continue
                try: msgs=messages(d)
                except Exception as ex: raise RuntimeError((archive,pi,ei)) from ex
                if not msgs: continue
                key=f'{archive}_{pi}_{ei}'
                record={'key':key,'archive':archive,'pack':pi,'entry':ei,'id':e[0],'type':e[1],'ref':e[2],'language':{0x10:'shared',0x20:'ja',0x30:'en'}[lang],'count':len(msgs),'size':len(d),'sha256':hashlib.sha256(d).hexdigest(),'message_ids':sorted(msgs)}
                resources.append(record)
                rows=[{'id':mid,'source':decode(raw),'raw':raw.hex()} for mid,raw in msgs.items()]
                (out/'source'/f'{key}.json').write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding='utf-8')
    print(archive,'catalogued',len(resources),'resources',flush=True)
# Pair language resources by message IDs and the resource reference, preferring the same pack.
english=[r for r in resources if r.get('language')=='en']
for jp in [r for r in resources if r.get('language')=='ja']:
    candidates=[en for en in english if en['archive']==jp['archive'] and en['id']==jp['id'] and en['ref']==jp['ref'] and en['message_ids']==jp['message_ids']]
    if candidates: jp['english_reference']=min(candidates,key=lambda en:abs(en['pack']-jp['pack']))['key']
(out/'inventory.json').write_text(json.dumps(resources,ensure_ascii=False,indent=1),encoding='utf-8')
summary={lang:{'resources':sum(r.get('language')==lang for r in resources),'messages':sum(r.get('count',0) for r in resources if r.get('language')==lang)} for lang in ['ja','en','shared']}
(out/'inventory_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
