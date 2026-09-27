"""Report installed-build coverage without treating exported text as translated."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
inventory=json.loads((ROOT/'localization/inventory.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'build/manifest.json').read_text(encoding='utf-8'))
rows=[]
for record in inventory:
    if record.get('language')!='ja': continue
    key=f"{record['pack']}:{record['entry']}"
    translated=manifest['translations'].get(key,{}) if record['archive']=='0000' else {}
    assert {int(mid) for mid in translated}.issubset(record['message_ids'])
    rows.append({'resource':record['key'],'messages':record['count'],'translated':len(translated),'remaining':record['count']-len(translated),'complete':len(translated)==record['count'],'english_reference':record.get('english_reference')})
total=sum(r['messages'] for r in rows); done=sum(r['translated'] for r in rows)
report={'full_localization_complete':False,'counting':'Japanese message slots, including duplicate resources; not a unique-text count','catalogued_messages':total,'built_translated_messages':done,'remaining_message_slots':total-done,'font':'NanumSquare Neo Bold','game_runtime_checked':False,'deferred_duplicates':manifest.get('deferred_duplicates',[]),'resources':rows}
(ROOT/'localization/coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='resources'},ensure_ascii=False,indent=2))
