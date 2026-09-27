"""Re-decode cached raw exports without touching game archives."""
from pathlib import Path
import json,collections
from codec import decode
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'localization'
inventory=json.loads((folder/'inventory.json').read_text(encoding='utf-8'))
old_story=json.loads((ROOT/'tools/all_en_full.json').read_text(encoding='utf-8'))
story_by_hash={}
for record in inventory:
    if record.get('archive')=='0001' and record.get('language')=='en' and record.get('id')==58:
        ref=old_story.get(str(record['pack']))
        if ref: story_by_hash[record['sha256']]=dict(ref)
counts=collections.Counter()
for record in inventory:
    if 'key' not in record: continue
    path=folder/'source'/(record['key']+'.json')
    rows=json.loads(path.read_text(encoding='utf-8'))
    references=story_by_hash.get(record['sha256'],{})
    for row in rows:
        row['source']=decode(bytes.fromhex(row['raw']),local=record['id']==58)
        row['decoding']='glyph_indices' if record['id']==58 else 'global_font'
        if row['id'] in references:
            row['english_visual_reference']=references[row['id']]
            row['reference_requires_review']=True
        if record.get('language')=='en':
            counts['english_messages']+=1
            counts['local_font_messages' if record['id']==58 else 'global_font_messages']+=1
            counts['unresolved_global_messages']+=record['id']!=58 and ('{G:' in row['source'] or len(row['source'].split('{RAW:')[-1])>200)
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding='utf-8')
(folder/'decoding_status.json').write_text(json.dumps(counts,indent=2),encoding='utf-8')
print(json.dumps(counts,indent=2))
