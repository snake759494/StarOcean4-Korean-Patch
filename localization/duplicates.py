"""Reuse authored text only for byte-identical Japanese global-font messages."""
from pathlib import Path
import json,re

def expand(translations):
    root=Path(__file__).resolve().parent
    candidates={}
    for key,authored in translations.items():
        rows=json.loads((root/'source'/('0000_'+key.replace(':','_')+'.json')).read_text(encoding='utf-8'))
        for row in rows:
            if row['id'] not in authored: continue
            if any(int(value)>=3073 for value in re.findall(r'\{G:(\d+)\}',row['source'])): continue
            raw=bytes.fromhex(row['raw']).rstrip(b'\0')
            if raw: candidates.setdefault(raw,set()).add(authored[row['id']])
    exact={raw:next(iter(options)) for raw,options in candidates.items() if len(options)==1}
    result={key:dict(values) for key,values in translations.items()}
    for resource in json.loads((root/'inventory.json').read_text(encoding='utf-8')):
        if resource.get('archive')!='0000' or resource.get('language')!='ja' or resource.get('id') not in (9,30): continue
        key=f"{resource['pack']}:{resource['entry']}"
        rows=json.loads((root/'source'/(resource['key']+'.json')).read_text(encoding='utf-8'))
        for row in rows:
            raw=bytes.fromhex(row['raw']).rstrip(b'\0')
            if raw in exact: result.setdefault(key,{}).setdefault(row['id'],exact[raw])
    return result
